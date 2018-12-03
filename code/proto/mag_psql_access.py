""" Test access to PostgreSQL DB `MAG`.
"""

import os
import json
import sys
from sqlalchemy import func, create_engine, Table
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

db_uri = 'postgresql+psycopg2://mag:1maG$@localhost:5432/MAG'
engine = create_engine(db_uri)
Base.metadata.create_all(engine)
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

Paper = Table('papers', Base.metadata, autoload=True, autoload_with=engine)

# print([c.name for c in Paper.columns])
# 'papertitle', 'originaltitle'
q = ('al. Unconsstrained handwritten character recognition based on fuzzy'
     'logic. Pattern')
q_easy = ('Fun with Fonts: Algorithmic Typography')
paper_db = session.query(Paper).\
    filter_by(originaltitle=q_easy).first()
if paper_db:
    # print(paper_db.keys())
    print(paper_db.paperid)
else:
    print('not found')
