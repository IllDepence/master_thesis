""" Generate datasets from a parsed and matched arXiv dump
"""

import json
import os
import re
import sys
from gensim.parsing.preprocessing import (preprocess_documents,
                                          preprocess_string,
                                          strip_multiple_whitespaces,
                                          strip_punctuation)
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from db_model import Base, Bibitem, BibitemArxivIDMap

CITE_PATT = re.compile((r'\{\{cite:([0-9A-F]{8}-[0-9A-F]{4}-4[0-9A-F]{3}'
                         '-[89AB][0-9A-F]{3}-[0-9A-F]{12})\}\}'), re.I)


def find_adjacent_citations(adfix, uuid_aid_map, backwards=False):
    """ Given text after or before a citation, find all directly adjacent
        citations.
    """

    if backwards:
        perimeter = adfix[-50:]
    else:
        perimeter = adfix[:50]
    match = CITE_PATT.search(perimeter)
    if not match:
        return []
    uuid = match.group(1)
    if uuid not in uuid_aid_map:
        return []
    aid = uuid_aid_map[uuid]
    margin = perimeter.index(match.group(0))
    if backwards:
        adfix = adfix[:-(50-margin)]
    else:
        adfix = adfix[45+margin:]
    moar = find_adjacent_citations(adfix, uuid_aid_map, backwards=backwards)
    return [aid] + moar


def generate(in_dir, db_uri=None, context_size=100, min_contexts=4,
             with_placeholder=True, preprocess=False):
    """ Generate a list of citation contexts, given criteria:
            context_size (in words)
            min_contexts
            with_placeholder
            preprocess  (preprocess_documents default; if off only punctuation
                         and multiple whitespaces are removed)

        If no db_uri is given, a SQLite file metadata.db is expected in in_dir.
    """

    if not db_uri:
        db_path = os.path.join(in_dir, 'metadata.db')
        db_uri = 'sqlite:///{}'.format(os.path.abspath(db_path))
    engine = create_engine(db_uri)
    Base.metadata.create_all(engine)
    Base.metadata.bind = engine
    DBSession = sessionmaker(bind=engine)
    session = DBSession()

    print('querying DB')
    have_global_id = session.query(BibitemArxivIDMap.arxiv_id).\
                        subquery()
    bibitems = session.query(Bibitem, BibitemArxivIDMap).\
                filter(Bibitem.uuid == BibitemArxivIDMap.uuid).\
                filter(BibitemArxivIDMap.arxiv_id.in_(have_global_id)).\
                all()
    print('merging bibitems')
    cited_docs_pre = {}
    uuid_aid_map = {}
    for bibitem in bibitems:
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
        for doc in doc_list:
            in_doc = doc['in_doc']
            fn = '{}.txt'.format(in_doc)
            text_file = os.path.join(in_dir, fn)
            with open(text_file) as f:
                text = f.read()
            marker = '{{{{cite:{}}}}}'.format(doc['uuid'])
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
        if len(tmp_list) >= min_contexts:
            contexts.extend(tmp_list)
    print(len(contexts))
    with open('items.csv', 'w') as f:
        for vals in contexts:
            line = '{}\n'.format(','.join(vals))
            f.write(line)

if __name__ == '__main__':
    if len(sys.argv) not in [2, 3]:
        print(('usage: python3 generate_dataset.py </path/to/in/dir> [<db_uri>'
               ']'))
        sys.exit()
    in_dir = sys.argv[1]
    if len(sys.argv) == 3:
        db_uri = sys.argv[2]
        ret = generate(in_dir, db_uri=db_uri)
    else:
        ret = generate(in_dir)
    if not ret:
        sys.exit()
