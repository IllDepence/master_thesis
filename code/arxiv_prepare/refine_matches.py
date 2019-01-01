""" Match bibitem strings to MAG IDs
"""

import datetime
import json
import os
import re
import requests
import sys
import time
import unidecode
from operator import itemgetter
from sqlalchemy import (create_engine, Column, Integer, String, UnicodeText,
                        Table, func)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError
from sqlalchemy.ext.declarative import declarative_base
from db_model import (Base, Bibitem, BibitemArxivIDMap, BibitemMAGIDMap,
                      BibitemLinkMap)


def mag_normalize(s):
    """ Normalize a string the same way paper titles are normalized in the MAG.

        - replace everything that is not a \w word character (letters, numbers
          and _, strangely) with a space
        - turn modified alphabet characters like Umlauts or accented characters
          into their "origin" (e.g. ä→a or ó→o)
        - replace multiple spaces with single ones
    """

    s = re.sub('[^\w]', ' ', s)
    s = re.sub('\s+', ' ', s)
    s = unidecode.unidecode(s)
    return s.strip().lower()


def MAG_paper_authors(db_engine, mid):
    tuples = db_engine.execute(
        ('select normalizedname from authors where authorid in (select'
         ' authorid from paperauthoraffiliations where paperid = \'{}\')'
         '').format(mid)
        ).fetchall()
    names = []
    for tupl in tuples:
        names.extend([n for n in tupl[0].split() if len(n) > 1])
    return names


def MAG_same_title_papers(db_engine, mid):
    tuples = db_engine.execute(
        ('select paperid, citationcount from papers where papertitle = (select'
         ' papertitle from papers where paperid = \'{}\')'
         '').format(mid)
        ).fetchall()
    return tuples


def match(db_uri=None, in_dir=None):
    """ Check and fix matches of bibitem strings to MAG IDs
    """

    if not (db_uri or in_dir):
        print('need either DB URI or input directory path')
        return False
    if in_dir:
        db_path = os.path.join(in_dir, 'metadata.db')
        db_uri = 'sqlite:///{}'.format(os.path.abspath(db_path))
    print('Setting up preliminary bibitem DB connection')
    engine = create_engine(db_uri)

    print('Querying bibitem DB')
    bibitem_tuples = engine.execute(
        ('select bibitem.uuid, in_doc, bibitem_string, mag_id from bibitem'
         ' join bibitemmagidmap on bibitem.uuid = bibitemmagidmap.uuid'
         '')).fetchall()
    #     '')).fetchmany(100)

    Base.metadata.create_all(engine)
    Base.metadata.bind = engine
    DBSession = sessionmaker(bind=engine)
    session = DBSession()

    # set up MAG DB
    print('setting up MAG DB')
    MAGBase = declarative_base()

    mag_db_uri = 'postgresql+psycopg2://mag:1maG$@localhost:5432/MAG'
    mag_engine = create_engine(mag_db_uri,
        connect_args={'options': '-c statement_timeout=60000'}
        )
    MAGBase.metadata.create_all(mag_engine)
    MAGBase.metadata.bind = mag_engine
    MAGDBSession = sessionmaker(bind=mag_engine)
    mag_session = MAGDBSession()

    MAGPaper = Table('papers', MAGBase.metadata,
                     autoload=True, autoload_with=mag_engine)
    MAGPaper = Table('papers', MAGBase.metadata,
                     autoload=True, autoload_with=mag_engine)
    # /set up MAG DB

    total = len(bibitem_tuples)
    num_changed = 0
    for bi_idx, bibitem_tuple in enumerate(bibitem_tuples):
        # for each matched bibitem
        uuid = bibitem_tuple[0]
        in_doc = bibitem_tuple[1]
        bibitem_string = bibitem_tuple[2]
        mid = bibitem_tuple[3]
        bibitem_string_normalized = mag_normalize(bibitem_string)
        # get all papers w/ identical title
        candidates = MAG_same_title_papers(mag_engine, mid)
        if len(candidates) < 2:
            continue
        # print('- - - - - - - - -')
        # print(bibitem_string_normalized)
        # print('- - - - - - - - -')
        # print('{} candidates'.format(len(candidates)))
        good_candidates = []
        for c in candidates:
            author_names = MAG_paper_authors(mag_engine, c[0])
            # print('    {} ({})'.format(c, author_names))
            for name in author_names:
                if name in bibitem_string_normalized:
                    good_candidates.append(c)
                    break
        # print()
        # print('{} good_candidates'.format(len(good_candidates)))
        # print('{}'.format(good_candidates))
        if len(good_candidates) == 0:
            continue
        elif len(good_candidates) == 1:
            choice = good_candidates[0]
        else:
            good_candidates = sorted(good_candidates,
                                     key=itemgetter(1),
                                     reverse=True)
            choice = good_candidates[0]
        # print()
        # print('choice: {}'.format(choice))
        # input()
        # print()
        new_mid = str(choice[0])
        magIDmap_db = session.query(BibitemMAGIDMap).\
            filter_by(uuid=uuid).first()
        if magIDmap_db.mag_id != new_mid:
            num_changed += 1
            magIDmap_db.mag_id = new_mid
            session.flush()
        if bi_idx%1000 == 0:
            print('{}/{} ({} updated)'.format(bi_idx, total, num_changed))
            session.commit()
    return 'done'


if __name__ == '__main__':
    if len(sys.argv) != 3 or (sys.argv[1] not in ['path', 'uri']):
        print(('usage: python3 parse_latex_tralics.py path|uri </path/to/in/di'
               'r>|<db_uri>'))
        sys.exit()
    path = sys.argv[1] == 'path'
    arg = sys.argv[2]
    if path:
        ret = match(in_dir=arg)
    else:
        ret = match(db_uri=arg)
    if not ret:
        sys.exit()
