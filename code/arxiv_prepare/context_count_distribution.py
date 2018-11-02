""" Generate datasets from a parsed and matched arXiv dump

    TODO:
        - for LARGER sample, create plot of number of contexts per cited doc
          (many 1s, few 2s, etc. long tail)
"""

import json
import os
import re
import sys
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from db_model import Base, Bibitem, BibitemArxivIDMap

CITE_PATT = re.compile((r'\{\{cite:[0-9A-F]{8}-[0-9A-F]{4}-4[0-9A-F]{3}-[89AB]'
                         '[0-9A-F]{3}-[0-9A-F]{12}\}\}'), re.I)


def generate(in_dir, db_uri=None):
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
                having(func.count(BibitemArxivIDMap.arxiv_id) > 1).\
                subquery()
    non_unique = session.query(Bibitem, BibitemArxivIDMap).\
                filter(BibitemArxivIDMap.arxiv_id.in_(sub)).\
                filter(Bibitem.uuid == BibitemArxivIDMap.uuid).all()
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
        # nu.BibitemArxivIDMap.arxiv_id
        edx = idx+len(marker)
        pre = text[:idx]
        post = text[edx:]
        pre = re.sub(CITE_PATT, '', pre)
        pre = re.sub(r'([^\w\s]+|\n)', '', pre)
        post = re.sub(CITE_PATT, '', post)
        post = re.sub(r'([^\w\s]+|\n)', '', post)
        window = 30
        print('>{}[42]{}<'.format(pre[-window:], post[:window]))

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
