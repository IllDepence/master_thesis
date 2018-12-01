""" Match bibitem strings to MAG IDs

    TODO:
        - if false positives too high, check authors
"""

import datetime
import json
import os
import pysolr
import re
import requests
import sys
from lxml import etree
from fuzzywuzzy import fuzz
from random import shuffle
from sqlalchemy import create_engine, Column, Integer, String, UnicodeText
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from db_model import (Base, Bibitem, BibitemArxivIDMap, BibitemMAGIDMap,
                      BibitemLinkMap)

DOI_PATT = re.compile(r'10.\d{4,9}/[-._;()/:A-Z0-9]+$', re.I)
IN_PJ_START_PATT = re.compile(
    r'^(in)?\s*(the)?\s*(Proceedings|Journal)\s+of', re.I)
TRANSACTIONS_START_PATT = re.compile(
    r'^\s*[\w\/]+?\s*(Transactions)\s+on', re.I)
IN_STH_PATT = re.compile(
    '(In\s+)?(the\s+)?(Proceedings|Journal|Transactions)\s+(of|on)\s+(the\s+)?\w+',
    re.I)
PAGE_VOL_START_PATT = re.compile(
    r'^\s*,?\s*(pages?|pp|vol(ume)?s?)\.?\s+\d', re.I)
ARXIV_URL_PATT_END = re.compile(
    r'arxiv\.org\/[a-z0-9-]{1,10}\/(([a-z0-9-]{1,15}\/)?[\d\.]{5,10}(v\d)?$)',
    re.I)
ARXIV_URL_PATT = re.compile(
    r'arxiv\.org\/[a-z0-9-]{1,10}\/(([a-z0-9-]{1,15}\/)?[\d\.]{4,9}\d)',
    re.I)
ARXIV_ID_PATT = re.compile(
    r'arXiv:(([a-z0-9-]{1,15}\/)?[\d\.]{4,9}\d)', re.I)
NAME_LIST_PATT = re.compile(
   r'^(([A-ZÀ-ÖØ-öø-ÿ].\s+){1,3}[A-ZÀ-ÖØ-öø-ÿ][a-zÀ-ÖØ-öø-ÿ\'-]+(,?\sand|,)\s+)+',
   re.I)
solr = pysolr.Solr('http://localhost:8983/solr/mag_papers/', timeout=600)


def send_query(query, debug=False):
    base_url = 'http://localhost:8983/solr/mag_papers/select?q='
    try:
        resp = requests.get(base_url + query)
    except requests.exceptions.ConnectionError:
        print('can\'t connect so Solr ... exiting')
        sys.exit()
    if resp.status_code != 200:
        # print('unexpected API response: {}\n{}'.format(resp.status_code,
        #                                                resp.text))
        return False
    resp_json = resp.json()
    num_results = resp_json.get('response', {}).get('numFound', 0)
    if num_results < 1:
        # print('No results')
        return False
    docs = resp_json.get('response', {}).get('docs', [{}])
    if debug:
        print('Top 10 results:')
        for doc in docs[:10]:
            print('        - {}'.format(doc.get('original_title', '')))
    return docs


def send_query_pysolr(title):
    title = re.sub('[^\w\s\d_]+', ' ', title)
    title = re.sub('\s+', ' ', title)
    resp = solr.search('normalized_title:"{}"'.format(title))
    if len(resp) < 1:
        cut_resp = []
        for cutoff in range(1, 6):
            cut = ' '.join(title.split(' ')[cutoff:])
            r = solr.search('normalized_title:"{}"'.format(cut))
            cut_resp.extend(list(r))
        for cutoff in range(1, 6):
            cut = ' '.join(title.split(' ')[:-cutoff])
            r = solr.search('normalized_title:"{}"'.format(cut))
            cut_resp.extend(list(r))
    return list(resp)


def parscit_parse(text):
    url = 'http://localhost:8000/parscit/parse'
    ret = requests.post(url, json={'string':text})
    if ret.status_code != 200:
        return False, False
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
    return title, journal


def clean(s):
    s = re.sub('[^\w\s]+', '', s)
    s = re.sub('\s+', ' ', s)
    return s.strip().lower()


def remove_name_list(text):
    return NAME_LIST_PATT.sub('', text)


def remove_containing_work(text):
    return IN_STH_PATT.sub('', text)


def find_arxiv_id(text):
    match = ARXIV_ID_PATT.search(text)
    if match:
        return match.group(1)
    else:
        match = ARXIV_URL_PATT.search(text)
        if match:
            return match.group(1)
    return False


def clean_by_segments(text_with_delim):
    segments = text_with_delim.split('¦')
    clean_title = ''
    for seg in segments:
        if IN_PJ_START_PATT.search(seg):
            break
        elif TRANSACTIONS_START_PATT.search(seg):
            break
        elif PAGE_VOL_START_PATT.search(seg):
            break
        elif ARXIV_URL_PATT_END.search(seg):
            m = ARXIV_URL_PATT_END.search(seg)
            if len(m.group(0))/len(seg) > .8:
                break
        clean_title += seg
    return clean_title


def check_result(bibitem_string, result_doc):
    """ For a result doc to pass as fitting require that:

            - the original title is (with some leeway) contained in the bibitem
              string
    """

    clean_bibitem_title = clean(bibitem_string)
    clean_result_title = clean(result_doc.get('original_title', False))
    if not clean_result_title:
        return False
    # check for exact title match
    exact_title = clean_result_title in clean_bibitem_title
    if exact_title:
        return True
    sim = 0
    if len(clean_bibitem_title) < len(clean_result_title):
        # just match
        sim = fuzz.ratio(clean_bibitem_title, clean_result_title)
    else:
        # sliding window
        steps = len(clean_bibitem_title) - len(clean_result_title) + 1
        for shift in range(steps):
            window = clean_bibitem_title[shift:shift+len(clean_result_title)]
            window_sim = fuzz.ratio(window, clean_result_title)
            sim = max(window_sim, sim)
    return sim > 94


def title_query_words_simple(text):
    words = [w for w in text.split()]
    query_string = '%2B'.join(words)
    return 'original_title:{0}'.format(query_string)


def title_query_words(text):
    with open('stopwords.txt') as f:
        stop_lines = f.readlines()
    stop_words = [line.strip() for line in stop_lines]
    clean_text = re.sub('[^\w\s]+', ' ', text)
    cleaner_text = re.sub('[0-9]+', '', clean_text)
    words = [w for w in cleaner_text.split(' ') if
             len(w) > 2 and w not in stop_words]
    query_string = '%2B'.join(words)
    return 'original_title:{0}'.format(query_string)


def match(db_uri=None, in_dir=None):
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

    arxiv_base_url = 'http://export.arxiv.org/api/query?search_query=id:'
    arxiv_ns = {'atom': 'http://www.w3.org/2005/Atom',
                'opensearch': 'http://a9.com/-/spec/opensearch/1.1/'}
    doi_base_url = 'https://data.crossref.org/'
    doi_headers = {'Accept': 'application/citeproc+json'}

    bibitems_db = session.query(Bibitem).all()
    shuffle(bibitems_db)
    num_matches = 0
    num_checked = 0
    num_false_positives = 0
    num_phys_rev = 0
    num_by_aid = 0
    num_by_aid_fail = 0
    num_by_doi = 0
    num_by_doi_fail = 0
    num_no_title = 0
    bi_total = len(bibitems_db)
    by_aid_total_time = 0
    by_aid_total_acc = 0
    by_doi_total_time = 0
    by_doi_total_acc = 0
    by_parscit_total_time = 0
    by_parscit_total_acc = 0
    solr_total_time = 0
    solr_total_acc = 0
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
            try:
                t1 = datetime.datetime.now()
                resp = requests.get(
                        '{}{}'.format(doi_base_url, given_doi),
                        headers=doi_headers)
                doi_metadata = json.loads(resp.text)
                title = doi_metadata.get('title', False)
                if title and len(title) > 0:
                    text = title
                    text_orig = text
                    num_by_doi += 1
                    doi_success = True
                t2 = datetime.datetime.now()
                d = t2 - t1
                by_doi_total_time += d.total_seconds()
                by_doi_total_acc += 1
            # except json.decoder.JSONDecodeError:
            except:
                pass
        if not (arxiv_id_success or doi_success):
            t1 = datetime.datetime.now()
            text_orig = text.replace('¦', '')
            if 'Phys. Rev.' in text_orig:
                num_phys_rev += 1
            # text = clean_by_segments(text)
            # text = remove_name_list(text)
            # text = remove_containing_work(text)
            text, journal = parscit_parse(text_orig)
            t2 = datetime.datetime.now()
            d = t2 - t1
            by_parscit_total_time += d.total_seconds()
            by_parscit_total_acc += 1
            if not text:
                num_no_title += 1
                # if journal:
                #     with open('no_title_journals', 'a') as f:
                #         line = '{}\t{}\n'.format(
                #             journal,
                #             text_orig
                #             )
                #         f.write(line)
                continue

        t1 = datetime.datetime.now()
        # q = title_query_words_simple(text)
        # if not q:
        #     continue
        # solr_resps = send_query(q)
        solr_resps = send_query_pysolr(text)
        t2 = datetime.datetime.now()
        d = t2 - t1
        solr_total_time += d.total_seconds()
        solr_total_acc += 1

        if solr_resps:
            for resp_idx in range(len(solr_resps)):
                t1 = datetime.datetime.now()
                candidate = solr_resps[resp_idx]
                solr_match = check_result(text_orig, candidate)
                t2 = datetime.datetime.now()
                d = t2 - t1
                check_total_time += d.total_seconds()
                check_total_acc += 1
                if solr_match:
                    # print('-> matched at result pos. #{}'.format(resp_idx+1))
                    solr_resp = candidate
                    break
        else:
            solr_match = False
            if arxiv_id_success:
                num_by_aid_fail += 1
            if doi_success:
                num_by_doi_fail += 1
        if not solr_match and solr_resps and not 'Phys. Rev.' in text_orig:
            continue
            # # check fails
            # print('- - - - - - - - - - - - - - - - - - - - - - - - - - -')
            # print('in doc: {}'.format(in_doc))
            # print('original text: {}'.format(text_orig))
            # print('query text:    {}'.format(text))
            # print('cleaned:       {}'.format(clean(text)))
            # print('found in non of:')
            # for resp_idx in range(len(solr_resps)):
            #     rtext = solr_resps[resp_idx].get('original_title', '')
            #     print('    {}'.format(rtext))
            #     print('    ({})\n'.format(clean(rtext)))
            # input()
        # print('.')
        # continue

        if solr_match:
            num_matches += 1
            mag_id = solr_resp.get('paper_id', False)
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
            result_doi = solr_resp.get('doi', False)
            if given_doi and result_doi:
                num_checked += 1
                if not given_doi.lower() == result_doi.lower():
                    num_false_positives += 1
                    # print('identified {}'.format(result_doi))
                    # print('but should\'ve been {}'.format(given_doi))
                    # input()
        # print('- - - [{}.{} s] - - -'.format(d.total_seconds(), d.microseconds))
        # print('enter to continue')
        # input()
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
        print('>>> avg time aID: {:.2f}'.format(by_aid_total_time/max(by_aid_total_acc, 1)))
        print('>>> avg time DOI: {:.2f}'.format(by_doi_total_time/max(by_doi_total_acc, 1)))
        print('>>> avg time ParsCit: {:.2f}'.format(by_parscit_total_time/max(by_parscit_total_acc, 1)))
        print('>>> avg time Solr: {:.2f}'.format(solr_total_time/max(solr_total_acc, 1)))
        print('>>> avg time check: {:.2f}'.format(check_total_time/max(check_total_acc, 1)))
        print('>>> avg time DB r: {:.2f}'.format(db_total_time/max(db_total_acc, 1)))
        print('>>> avg time DB w: {:.2f}'.format(db_w_total_time/max(db_w_total_acc, 1)))
    session.commit()
    print('>>> time aID: {:.2f}'.format(by_aid_total_time))
    print('>>> time DOI: {:.2f}'.format(by_doi_total_time))
    print('>>> time ParsCit: {:.2f}'.format(by_parscit_total_time))
    print('>>> time Solr: {:.2f}'.format(solr_total_time))
    print('>>> time check: {:.2f}'.format(check_total_time))
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
