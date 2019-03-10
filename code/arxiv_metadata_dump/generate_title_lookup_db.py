""" .
"""

import os
import json
import sys
from lxml import etree
from random import shuffle
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from sqlalchemy import Column, Integer, String, UnicodeText, ForeignKey
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Paper(Base):
    __tablename__ = 'paper'
    id = Column(Integer(), autoincrement=True, primary_key=True)
    aid = Column(String(36))
    title = Column(UnicodeText())

db_uri = 'sqlite:///aid_title.db'
engine = create_engine(db_uri)
Base.metadata.create_all(engine)
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

ns = {'oai':'http://www.openarchives.org/OAI/2.0/',
      'dc':'http://purl.org/dc/elements/1.1/',
      'oai_dc':'http://www.openarchives.org/OAI/2.0/oai_dc/',
      'xsi':'http://www.w3.org/2001/XMLSchema-instance'}

parser = etree.XMLParser()
#dump_dir = '/vol1/arxiv/metadata/newArxivMetaHarvesting201712'
dump_dir = sys.argv[1]

month_field_docs = {}
for idx, fn in enumerate(os.listdir(dump_dir)):
    if os.path.splitext(fn)[1] != '.xml':
        continue
    path = os.path.join(dump_dir, fn)
    with open(path) as f:
        tree = etree.parse(f, parser)
    for rec in tree.xpath('/oai:OAI-PMH/oai:ListRecords/oai:record',
                          namespaces=ns):
        header = rec.find('oai:header', namespaces=ns)
        field = header.find('oai:setSpec', namespaces=ns).text
        field = field.split(':')[0]
        id_text = header.find('oai:identifier', namespaces=ns).text
        aid = id_text.split(':')[-1]
        meta = rec.find('oai:metadata', namespaces=ns)
        try:
            title = meta.getchildren()[0].find('dc:title', namespaces=ns).text
        except AttributeError:
            continue

        paper_db = Paper(aid=aid, title=title)
        session.add(paper_db)
        session.flush()
    if idx % 100 == 0:
        print(idx)
        session.commit()
session.commit()
