""" JUST A COPY
"""

from sqlalchemy import Column, Integer, String, UnicodeText, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Bibitem(Base):
    __tablename__ = 'bibitem'
    uuid = Column(String(36), primary_key=True)
    in_doc = Column(String(36))
    bibitem_string = Column(UnicodeText())


class BibitemLinkMap(Base):
    __tablename__ = 'bibitemlinkmap'
    id = Column(Integer(), autoincrement=True, primary_key=True)
    uuid = Column(String(36), ForeignKey('bibitem.uuid'))
    link = Column(UnicodeText())


class BibitemArxivIDMap(Base):
    __tablename__ = 'bibitemarxividmap'
    id = Column(Integer(), autoincrement=True, primary_key=True)
    uuid = Column(String(36), ForeignKey('bibitem.uuid'))
    arxiv_id = Column(String(36))
