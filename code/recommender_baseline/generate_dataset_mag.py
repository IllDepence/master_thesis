""" Generate datasets from MAG DB
"""

import json
import os
import re
import sys
from gensim.parsing.preprocessing import (preprocess_documents,
                                          preprocess_string,
                                          strip_multiple_whitespaces,
                                          strip_punctuation)
from sqlalchemy import func, create_engine, Table
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base


def generate(db_uri, min_contexts=4, preprocess=False):
    """ Generate a list of citation contexts, given criteria:
            min_contexts
            preprocess  (preprocess_documents default; if off only punctuation
                         and multiple whitespaces are removed)
    """

    Base = declarative_base()

    engine = create_engine(db_uri)
    Base.metadata.create_all(engine)
    Base.metadata.bind = engine
    DBSession = sessionmaker(bind=engine)
    session = DBSession()

    CitContext = Table('papercitationcontexts', Base.metadata, autoload=True,
                       autoload_with=engine)

    print('querying DB')
    non_unique = session.query(CitContext.columns.paperreferenceid).\
         group_by(CitContext.columns.paperreferenceid).\
         having(func.count(CitContext.columns.paperreferenceid)
                 > min_contexts-1).\
         subquery()

    cit_contexts_db = session.query(CitContext).\
        filter(CitContext.columns.paperreferenceid.in_(non_unique)).\
        all()  # order_by(BibitemArxivIDMap.arxiv_id.desc()).all()
    print(len(cit_contexts_db))
    # 187595127
    print(dir(cit_contexts_db[0]))
    # ['__add__', '__class__', '__contains__', '__delattr__', '__dir__',
    #  '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__',
    #  '__getitem__', '__getnewargs__', '__gt__', '__hash__', '__init__',
    #  '__init_subclass__', '__iter__', '__le__', '__len__', '__lt__',
    #  '__module__', '__mul__', '__ne__', '__new__', '__reduce__',
    #  '__reduce_ex__', '__repr__', '__rmul__', '__setattr__', '__sizeof__',
    #  '__slots__', '__str__', '__subclasshook__', '_asdict', '_fields',
    #  '_real_fields', 'citationcontext', 'count', 'index', 'keys', 'paperid',
    #  'paperreferenceid']
    # 
    # Work in progress. ↑ MAG DB results ↓ stuff to adjust for generating
    #                                      a dataset
    # 
    sys.exit()

    print('merging bibitems')
    cited_docs_pre = {}
    uuid_aid_map = {}
    for bibitem in bibitems:
        if global_ids == 'mag':
            aid = bibitem.BibitemMAGIDMap.mag_id
        else:
            aid = bibitem.BibitemArxivIDMap.arxiv_id
        uuid = bibitem.Bibitem.uuid
        uuid_aid_map[uuid] = aid
        in_doc = bibitem.Bibitem.in_doc
        if aid not in cited_docs_pre:
            cited_docs_pre[aid] = {}
        if in_doc not in cited_docs_pre[aid]:
            cited_docs_pre[aid][in_doc] = []
        cited_docs_pre[aid][in_doc].append(uuid)
    print('checking merging results')
    cited_docs = {}
    for aid, doc_dict in cited_docs_pre.items():
        # for evaluation we *need* at least 2 documents containing citation
        # contexts (in order to perform a per doc test/train split)
        if len(doc_dict) > 1:
            cited_docs[aid] = []
            for in_doc, uuid_list in doc_dict.items():
                cited_docs[aid].append({
                    'uuid': uuid_list[0],  # uuid_list should always be len. 1
                    'in_doc': in_doc
                    })
    print('going through docs')
    contexts = []
    for aid, doc_list in cited_docs.items():
        tmp_list = []
        num_docs = 0
        for doc in doc_list:
            in_doc = doc['in_doc']
            fn = '{}.txt'.format(in_doc)
            text_file = os.path.join(in_dir, fn)
            with open(text_file) as f:
                text = f.read()
            marker = '{{{{cite:{}}}}}'.format(doc['uuid'])
            marker_found = False
            for m in re.finditer(marker, text):
                margin = int(context_size/2)
                idx = m.start()
                edx = m.end()
                pre = text[:idx]
                post = text[edx:]
                adj_pre = find_adjacent_citations(pre, uuid_aid_map,
                                                  backwards=True)
                adj_post = find_adjacent_citations(post, uuid_aid_map)
                adjacent_citations = adj_pre + adj_post
                pre = re.sub(CITE_PATT, '', pre)
                post = re.sub(CITE_PATT, '', post)
                # heuristic pre-cutting (10 times average word length)
                pre = pre[-margin*6*10:]
                post = post[:margin*6*10]
                if preprocess:
                    pre, post = preprocess_documents([pre, post])
                else:
                    custom_filter = [strip_punctuation,
                                     strip_multiple_whitespaces]
                    pre = preprocess_string(pre, custom_filter)
                    post = preprocess_string(post, custom_filter)
                placeholder = ''
                if with_placeholder:
                    placeholder = ' [] '
                context = '{}{}{}'.format(' '.join(pre[-margin:]),
                                          placeholder,
                                          ' '.join(post[:margin]))
                adj_cit_str = '[{}]'.format('|'.join(adjacent_citations))
                tmp_list.append([aid, adj_cit_str, in_doc, context])
                marker_found = True
            if marker_found:
                num_docs += 1
        if len(tmp_list) >= min_contexts and num_docs > 1:
            contexts.extend(tmp_list)
    print(len(contexts))
    with open('items.csv', 'w') as f:
        for vals in contexts:
            line = '{}\n'.format(','.join(vals))
            f.write(line)

if __name__ == '__main__':
    if len(sys.argv) >= 2:
        db_uri = sys.argv[1]
    else:
        db_uri = 'postgresql+psycopg2://mag:1maG$@localhost:5432/MAG'
        print('using default DB URI {}'.format(db_uri))
    ret = generate(db_uri)
    if not ret:
        sys.exit()
