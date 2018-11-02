""" Generate datasets from a parsed and matched arXiv dump
"""

import json
import os
import re
import sys
from gensim.parsing.preprocessing import preprocess_documents
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from db_model import Base, Bibitem, BibitemArxivIDMap

CITE_PATT = re.compile((r'\{\{cite:[0-9A-F]{8}-[0-9A-F]{4}-4[0-9A-F]{3}-[89AB]'
                         '[0-9A-F]{3}-[0-9A-F]{12}\}\}'), re.I)


def generate(in_dir, db_uri=None, context_size=100, min_contexts=4,
             with_placeholder=True):
    """ Generate a list of citation contexts, given criteria:
            context_size (in words)
            min_contexts
            with_placeholder

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

    sub = session.query(BibitemArxivIDMap.arxiv_id).\
                group_by(BibitemArxivIDMap.arxiv_id).\
                having(func.count(BibitemArxivIDMap.arxiv_id)
                        > min_contexts-1).\
                subquery()
    non_unique = session.query(Bibitem, BibitemArxivIDMap).\
                filter(BibitemArxivIDMap.arxiv_id.in_(sub)).\
                filter(Bibitem.uuid == BibitemArxivIDMap.uuid).all()
    items = []
    for nu in non_unique:
        fn = '{}.txt'.format(nu.Bibitem.in_doc)
        text_file = os.path.join(in_dir, fn)
        with open(text_file) as f:
            text = f.read()
        marker = '{{{{cite:{}}}}}'.format(nu.Bibitem.uuid)
        try:
            idx = text.index(marker)
        except ValueError:
            # Reference with no corresponding citation marker
            continue
            # print('{} | {} | {}'.format(
            #     nu.Bibitem.in_doc,
            #     nu.Bibitem.uuid,
            #     nu.BibitemArxivIDMap.arxiv_id))
        # TODO: retrieve metadata for cited document (and mby full text) and
        #       include it into dataset (description of cited doc = citation
        #       context + meta data)
        # nu.BibitemArxivIDMap.arxiv_id
        # QUESTION: input is only a prospective citation context, how to work
        #           in metadata/cited doc fulltext aspects?
        #
        # QUESTION: how to "encode" citation marker position?
        margin = int(context_size/2)
        edx = idx+len(marker)
        pre = text[:idx]
        post = text[edx:]
        pre = re.sub(CITE_PATT, '', pre)
        post = re.sub(CITE_PATT, '', post)
        # pre = re.sub(r'([^\w\s]+|\n)', '', pre)
        # post = re.sub(r'([^\w\s]+|\n)', '', post)
        # heuristic pre-cutting (10 times average word length)
        pre = pre[-margin*6*10:]
        post = post[:margin*6*10]
        pre, post = preprocess_documents([pre, post])
        placeholder = ''
        if with_placeholder:
            placeholder = ' [] '
        context = '{}{}{}'.format(' '.join(pre[-margin:]),
                                  placeholder,
                                  ' '.join(post[:margin]))
        cited_doc = nu.BibitemArxivIDMap.arxiv_id
        items.append((cited_doc, context))
        # print('>{}<'.format(cntxt))
    print(len(items))
    with open('items.csv', 'w') as f:
        for item in items:
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
