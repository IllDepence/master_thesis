""" Match bibitem strings to MAG IDs
"""

import datetime
import json
import os
import re
import requests
import sys
import unidecode
from sqlalchemy import (create_engine, Column, Integer, String, UnicodeText,
                        Table)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from db_model import (Base, Bibitem, BibitemArxivIDMap, BibitemMAGIDMap,
                      BibitemLinkMap)

DOI_PATT = re.compile(
    r'10.\d{4,9}/[-._;()/:A-Z0-9]+$', re.I)
ARXIV_URL_PATT = re.compile(
    r'arxiv\.org\/[a-z0-9-]{1,10}\/(([a-z0-9-]{1,15}\/)?[\d\.]{4,9}\d)', re.I)
ARXIV_ID_PATT = re.compile(
    r'arXiv:(([a-z0-9-]{1,15}\/)?[\d\.]{4,9}\d)', re.I)


def parscit_parse(text):
    """ Parse bibitem text using Neural-ParsCit docker container.
    """

    url = 'http://localhost:8000/parscit/parse'
    ret = requests.post(url, json={'string':text})
    if ret.status_code != 200:
        return False, False, False
    response = json.loads(ret.text)
    parsed_terms = response['data']
    title_terms = []
    journal_terms = []
    for parsed_term in parsed_terms:
        if parsed_term['entity'] == 'title':
            title_terms.append(parsed_term['term'])
        elif parsed_term['entity'] == 'journal':
            journal_terms.append(parsed_term['term'])
    if len(title_terms) == 0:
        title = False
    else:
        title = ' '.join(title_terms)
    if len(journal_terms) == 0:
        journal = False
    else:
        journal = ' '.join(journal_terms)
    return title, journal, parsed_terms


def clean(s):
    """ Generic string cleaning
    """

    s = re.sub('[^\w\s]+', '', s)
    s = re.sub('\s+', ' ', s)
    return s.strip().lower()


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


def title_by_doi(given_doi):
    """ Given a DOI, try to get a work's title using crossref.org
    """

    doi_base_url = 'https://data.crossref.org/'
    doi_headers = {'Accept': 'application/citeproc+json',
                   'User-Agent': ('DoiToTitleScript (working on a master thesi'
                                  's; mailto:tarek.saier@uranus.uni-freiburg.d'
                                  'e)')}
    try:
        resp = requests.get(
                '{}{}'.format(doi_base_url, given_doi),
                headers=doi_headers)
        rate_lim_lim = resp.headers.get('X-Rate-Limit-Limit', '9001')
        rate_lim_int = resp.headers.get(
            'X-Rate-Limit-Interval', '1s'
            ).replace('s', '')
    except requests.RequestException:
        return False
    try:
        wait = float(rate_lim_int)/float(rate_lim_lim)
        if resp.elapsed.total_seconds() < wait:
            delta = wait - resp.elapsed.total_seconds()
            time.sleep(delta)
    except ValueError:
        pass
    try:
        doi_metadata = json.loads(resp.text)
        title = doi_metadata.get('title', False)
        if title and len(title) > 0:
            return title
    except json.decoder.JSONDecodeError:
        return False


def guess_aps_journal_paper_doi(parscit_terms):
    """ American Physical Society Journals have predictable DOIs

        E.g.: Phys. Rev. B 84, 245128
           -> 10.1103/physrevb.84.245128
    """

    normalized_terms = []
    for term in parscit_terms:
        clean = re.sub(r'[^\w]', ' ', term['term'])
        cleaner = re.sub('\s+', ' ', clean)
        parts = [p.lower() for p in cleaner.split() if len(p) > 0]
        normalized_terms.extend(parts)
    normalized_text_orig = ' '.join(normalized_terms)
    # heuristic to guess DOI of APS journal papers
    if ' phys rev ' in normalized_text_orig or \
       ' rev mod phys ' in normalized_text_orig:
        if ' phys rev ' in normalized_text_orig:
            doi_start_idx = normalized_terms.index('phys')
            journal_terms = normalized_terms[doi_start_idx:doi_start_idx+3]
            try:
                vol = normalized_terms[doi_start_idx+3]
                aps_id = normalized_terms[doi_start_idx+4]
            except IndexError:
                return False
        elif ' rev mod phys ' in normalized_text_orig:
            doi_start_idx = normalized_terms.index('rev')
            journal_terms = normalized_terms[doi_start_idx:doi_start_idx+4]
            try:
                vol = normalized_terms[doi_start_idx+4]
                aps_id = normalized_terms[doi_start_idx+5]
            except IndexError:
                return False
        if re.match(r'^\d+$', vol) and re.match(r'^\d+$', aps_id):
            doi_guess = '10.1103/{}.{}.{}'.format(
                ''.join(journal_terms),
                vol,
                aps_id
                )
            return doi_guess
    return False


def find_arxiv_id(text):
    """ Loor for an arXiv ID within the given text.
    """

    match = ARXIV_ID_PATT.search(text)
    if match:
        return match.group(1)
    else:
        match = ARXIV_URL_PATT.search(text)
        if match:
            return match.group(1)
    return False


def match(db_uri=None, in_dir=None):
    """ Match bibitem strings to MAG IDs
    """

    if not (db_uri or in_dir):
        print('need either DB URI or input directory path')
        return False
    if in_dir:
        db_path = os.path.join(in_dir, 'metadata.db')
        db_uri = 'sqlite:///{}'.format(os.path.abspath(db_path))
    engine = create_engine(db_uri)
    Base.metadata.create_all(engine)
    Base.metadata.bind = engine
    DBSession = sessionmaker(bind=engine)
    session = DBSession()

    # set up arXiv ID DB
    AIDBase = declarative_base()

    class Paper(AIDBase):
        __tablename__ = 'paper'
        id = Column(Integer(), autoincrement=True, primary_key=True)
        aid = Column(String(36))
        title = Column(UnicodeText())

    aid_db_uri = 'sqlite:///aid_title.db'
    aid_engine = create_engine(aid_db_uri)
    AIDBase.metadata.create_all(aid_engine)
    AIDBase.metadata.bind = aid_engine
    AIDDBSession = sessionmaker(bind=aid_engine)
    aid_session = AIDDBSession()
    # /set up arXiv ID DB

    # set up MAG DB
    MAGBase = declarative_base()

    mag_db_uri = 'postgresql+psycopg2://mag:1maG$@localhost:5432/MAG'
    mag_engine = create_engine(mag_db_uri)
    MAGBase.metadata.create_all(mag_engine)
    MAGBase.metadata.bind = mag_engine
    MAGDBSession = sessionmaker(bind=mag_engine)
    mag_session = MAGDBSession()

    MAGPaper = Table('papers', MAGBase.metadata,
                     autoload=True, autoload_with=mag_engine)
    # /set up MAG DB

    arxiv_base_url = 'http://export.arxiv.org/api/query?search_query=id:'
    arxiv_ns = {'atom': 'http://www.w3.org/2005/Atom',
                'opensearch': 'http://a9.com/-/spec/opensearch/1.1/'}

    bibitems_db = session.query(Bibitem).all()
    num_matches = 0
    num_checked = 0
    num_false_positives = 0
    num_phys_rev = 0
    num_by_aid = 0
    num_by_aid_fail = 0
    num_by_doi = 0
    num_by_doi_fail = 0
    num_no_title = 0
    num_aps_doi_rebound = 0
    bi_total = len(bibitems_db)
    by_aid_total_time = 0
    by_aid_total_acc = 0
    by_doi_total_time = 0
    by_doi_total_acc = 0
    by_parscit_total_time = 0
    by_parscit_total_acc = 0
    magdb_total_time = 0
    magdb_total_acc = 0
    check_total_time = 0
    check_total_acc = 0
    db_total_time = 0
    db_total_acc = 0
    db_w_total_time = 0
    db_w_total_acc = 0
    for bi_idx, bibitem_db in enumerate(bibitems_db):
        if bi_idx%1000 == 0:
            session.commit()
        text = bibitem_db.bibitem_string
        in_doc = bibitem_db.in_doc
        aid = find_arxiv_id(text)
        arxiv_id_success = False
        if aid:
            t1 = datetime.datetime.now()
            apaper_db = aid_session.query(Paper).filter_by(aid=aid).first()
            if not apaper_db:
                # catch cases like quant-ph/0802.3625 (acutally 0802.3625)
                guess = aid.split('/')[-1]
                apaper_db = aid_session.query(Paper).filter_by(aid=guess).first()
            if not apaper_db and re.match(r'^\d+$', aid):
                # catch cases like 14025167 (acutally 1402.5167)
                guess = '{}.{}'.format(aid[:4], aid[4:])
                apaper_db = aid_session.query(Paper).filter_by(aid=guess).first()
            # cases not handled:
            # - arXiv:9409089v2[hep-th] -> hep-th/9409089
            if apaper_db:
                text = apaper_db.title.replace('\n', ' ')
                text = re.sub('\s+', ' ', text)
                text_orig = text
                num_by_aid += 1
                arxiv_id_success = True
                t2 = datetime.datetime.now()
                d = t2 - t1
                by_aid_total_time += d.total_seconds()
                by_aid_total_acc += 1
        t1 = datetime.datetime.now()
        bibitemlink_db = session.query(BibitemLinkMap).filter_by(
                                  uuid=bibitem_db.uuid).first()
        t2 = datetime.datetime.now()
        d = t2 - t1
        db_total_time += d.total_seconds()
        db_total_acc += 1
        given_doi = False
        if bibitemlink_db:
            if 'doi' in bibitemlink_db.link:
                m = DOI_PATT.search(bibitemlink_db.link)
                if m:
                    given_doi = m.group(0)
        doi_success = False
        if not arxiv_id_success and given_doi:
            t1 = datetime.datetime.now()
            doi_resp = title_by_doi(given_doi)
            if doi_resp:
                text = doi_resp
                text_orig = text
                num_by_doi += 1
                doi_success = True
            t2 = datetime.datetime.now()
            d = t2 - t1
            by_doi_total_time += d.total_seconds()
            by_doi_total_acc += 1
        parscit_title = False
        if not (arxiv_id_success or doi_success):
            t1 = datetime.datetime.now()
            text_orig = text.replace('¦', '')
            if 'Phys. Rev.' in text_orig:
                num_phys_rev += 1
            text, journal, parscit_terms = parscit_parse(text_orig)
            t2 = datetime.datetime.now()
            d = t2 - t1
            by_parscit_total_time += d.total_seconds()
            by_parscit_total_acc += 1
            parscit_title = True
        if not text and parscit_terms:
            doi_guess = guess_aps_journal_paper_doi(parscit_terms)
            if doi_guess:
                doi_resp = title_by_doi(doi_guess)
                if doi_resp:
                    text = doi_resp
                    text_orig = text
                    num_aps_doi_rebound += 1
        if not (arxiv_id_success or doi_success):
            if not text:
                num_no_title += 1
                continue

        t1 = datetime.datetime.now()
        if parscit_title:
            title_guesses = []
            normalized_title = mag_normalize(text)
            for lshift in range(3):
                for rshift in range(3):
                    words = normalized_title.split()
                    pick = words[lshift:(len(words)-rshift)]
                    if len(pick) >= 3:
                        title_guesses.append(' '.join(pick))
            for title_guess in title_guesses:
                mag_paper_db = mag_session.query(MAGPaper).\
                        filter_by(papertitle=normalized_title).first()
                if mag_paper_db:
                    break
        else:
            normalized_title = mag_normalize(text)
            mag_paper_db = mag_session.query(MAGPaper).\
                    filter_by(papertitle=normalized_title).first()
        t2 = datetime.datetime.now()
        d = t2 - t1
        magdb_total_time += d.total_seconds()
        magdb_total_acc += 1

        if mag_paper_db:
            magdb_match = True
            magdb_resp = {'paper_id': mag_paper_db.paperid}
            if 'doi' in mag_paper_db.keys() and mag_paper_db.doi:
                magdb_resp['doi'] = mag_paper_db.doi
        else:
            magdb_match = False
            if arxiv_id_success:
                num_by_aid_fail += 1
            if doi_success:
                num_by_doi_fail += 1

        if magdb_match:
            num_matches += 1
            mag_id = magdb_resp.get('paper_id', False)
            if mag_id:
                t1 = datetime.datetime.now()
                mag_id_db = BibitemMAGIDMap(
                    uuid=bibitem_db.uuid,
                    mag_id=mag_id
                    )
                # add to DB
                session.add(mag_id_db)
                session.flush()
                t2 = datetime.datetime.now()
                d = t2 - t1
                db_w_total_time += d.total_seconds()
                db_w_total_acc += 1
            result_doi = magdb_resp.get('doi', False)
            if given_doi and result_doi:
                num_checked += 1
                if not given_doi.lower() == result_doi.lower():
                    num_false_positives += 1
        print('- - - - - - - - - - - - - - - - -')
        print('{}/{}'.format(bi_idx+1, bi_total))
        print('matches: {}'.format(num_matches))
        print('checked: {}'.format(num_checked))
        print('Phys. Rev.: {}'.format(num_phys_rev))
        print('no title: {}'.format(num_no_title))
        print('maybe (!) false positives: {}'.format(num_false_positives))
        print('by arXiv ID: {}'.format(num_by_aid))
        print('by arXiv ID fail: {}'.format(num_by_aid_fail))
        print('by doi: {}'.format(num_by_doi))
        print('by doi fail: {}'.format(num_by_doi_fail))
        print('APS doi rebound: {}'.format(num_aps_doi_rebound))
        print('>>> avg time aID: {:.2f}'.format(by_aid_total_time/max(by_aid_total_acc, 1)))
        print('>>> avg time DOI: {:.2f}'.format(by_doi_total_time/max(by_doi_total_acc, 1)))
        print('>>> avg time ParsCit: {:.2f}'.format(by_parscit_total_time/max(by_parscit_total_acc, 1)))
        print('>>> avg time MAGDB: {:.2f}'.format(magdb_total_time/max(magdb_total_acc, 1)))
        print('>>> avg time DB r: {:.2f}'.format(db_total_time/max(db_total_acc, 1)))
        print('>>> avg time DB w: {:.2f}'.format(db_w_total_time/max(db_w_total_acc, 1)))
    session.commit()
    print('>>> time aID: {:.2f}'.format(by_aid_total_time))
    print('>>> time DOI: {:.2f}'.format(by_doi_total_time))
    print('>>> time ParsCit: {:.2f}'.format(by_parscit_total_time))
    print('>>> time MAGDB: {:.2f}'.format(magdb_total_time))
    print('>>> time DB r: {:.2f}'.format(db_total_time))
    print('>>> time DB w: {:.2f}'.format(db_w_total_time))


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
