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

CITE_PATT = re.compile((r'\{\{cite:[0-9A-F]{8}-[0-9A-F]{4}-4[0-9A-F]{3}-[89AB]'
                         '[0-9A-F]{3}-[0-9A-F]{12}\}\}'), re.I)


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
    sub = session.query(BibitemArxivIDMap.arxiv_id).\
                subquery()
    res = session.query(Bibitem, BibitemArxivIDMap).\
                filter(Bibitem.uuid == BibitemArxivIDMap.uuid).\
                filter(BibitemArxivIDMap.arxiv_id.in_(sub)).\
                all()
    print('merging bibitems')
    cited_docs = {}
    for bibitem in res:
        aid = bibitem.BibitemArxivIDMap.arxiv_id
        if aid not in cited_docs:
            cited_docs[aid] = []
        cited_docs[aid].append({
            'uuid': bibitem.Bibitem.uuid,
            'in_doc': bibitem.Bibitem.in_doc
            })
    print('going through docs')
    contexts = []
    for aid, doc_list in cited_docs.items():
        tmp_list = []
        for doc in doc_list:
            fn = '{}.txt'.format(doc['in_doc'])
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
                pre = re.sub(CITE_PATT, '', pre)
                post = re.sub(CITE_PATT, '', post)
                # heuristic pre-cutting (10 times average word length)
                pre = pre[-margin*6*10:]
                post = post[:margin*6*10]
                if preprocess:
                    pre, post = preprocess_documents([pre, post])
                else:
                    custom_filter = [strip_punctuation, strip_multiple_whitespaces]
                    pre = preprocess_string(pre, custom_filter)
                    post = preprocess_string(post, custom_filter)
                placeholder = ''
                if with_placeholder:
                    placeholder = ' [] '
                context = '{}{}{}'.format(' '.join(pre[-margin:]),
                                          placeholder,
                                          ' '.join(post[:margin]))
                tmp_list.append((aid, context))
        if len(tmp_list) >= min_contexts:
            contexts.extend(tmp_list)
    print(len(contexts))
    with open('items.csv', 'w') as f:
        for item in contexts:
            line = '{},{}\n'.format(item[0], item[1])
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
