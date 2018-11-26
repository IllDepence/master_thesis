""" Match bibitem strings to MAG IDs

    TODO:
        - if false positives too high, check authors
"""

import datetime
import json
import os
import re
import requests
import sys
from lxml import etree
from random import shuffle
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
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
    r'arxiv\.org\/[a-z0-9-]{1,10}\/(([a-z0-9-]{1,15}\/)?[\d\.]{5,10}(v\d)?)',
    re.I)
ARXIV_ID_PATT = re.compile(
    r'arXiv:(([a-z0-9-]{1,15}\/)?[\d\.]{5,10}(v\d)?)', re.I)
NAME_LIST_PATT = re.compile(
   r'^(([A-ZÀ-ÖØ-öø-ÿ].\s+){1,3}[A-ZÀ-ÖØ-öø-ÿ][a-zÀ-ÖØ-öø-ÿ\'-]+(,?\sand|,)\s+)+',
   re.I)


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


def parscit_get_title(text):
    url = 'http://localhost:8000/parscit/parse'
    ret = requests.post(url, json={'string':text})
    if ret.status_code != 200:
        return False
    response = json.loads(ret.text)
    parsed_terms = response['data']
    title_terms = []
    for parsed_term in parsed_terms:
        if parsed_term['entity'] == 'title':
            title_terms.append(parsed_term['term'])
    if len(title_terms) == 0:
        return False
    return ' '.join(title_terms)


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


def check_result(bibitem_string, result_doc, debug=False, strict=True):
    """ For a result doc to pass as fitting require that:

            - the original title is contained in the bibitem string
                OR
            - the bibitem string contains most of the original title's words in
              correct order
    """

    clean_orig = clean(bibitem_string)
    clean_result_title = clean(result_doc.get('original_title', ''))
    # check for exact title match
    exact_title = clean_result_title in clean_orig
    if debug:
        print('{}\nin\n{}\n→{}'.format(clean_result_title, clean_orig,
                                       exact_title))
    if exact_title:
        return True
    if strict:
        return False
    needles = clean_result_title.split(' ')
    haystack = clean_orig.split(' ')
    found_count = 0
    correct_order_count = 0
    last_index = -1
    for needle in needles:
        try:
            index = haystack.index(needle)
            found_count += 1
            if index > last_index:
                correct_order_count += 1
                last_index = index
        except ValueError:
            continue
    try:
        found_ratio = found_count / len(needles)
    except ZeroDivisionError:
        found_ratio = 0
    try:
        order_ratio = correct_order_count / found_count
    except ZeroDivisionError:
        order_ratio = 0
    if debug:
        print('found ratio: {}\norder ratio: {}'.format(found_ratio,
                                                        order_ratio))
    return found_ratio > 0.67 and order_ratio > 0.8


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
    num_no_title = 0
    bi_total = len(bibitems_db)
    for bi_idx, bibitem_db in enumerate(bibitems_db):
        t1 = datetime.datetime.now()
        text = bibitem_db.bibitem_string
        in_doc = bibitem_db.in_doc
        aid = ARXIV_ID_PATT.search(text)
        arxiv_api_success = False
        if aid:
            try:
                resp = requests.get(
                    '{}{}&start=0&max_results=1'.format(arxiv_base_url, aid))
                xml_root = etree.fromstring(resp.text.encode('utf-8'))
                result_elems = xml_root.xpath('/atom:feed/atom:entry',
                                              namespaces=arxiv_ns)
                result = result_elems[0]
                text = result.find('{http://www.w3.org/2005/Atom}title').text
                text_orig = text
                num_by_aid += 1
                arxiv_api_success = True
            except:
                pass
        doi_success = False
        bibitemlink_db = session.query(BibitemLinkMap).filter_by(
                                  uuid=bibitem_db.uuid).first()
        given_doi = False
        if bibitemlink_db:
            if 'doi' in bibitemlink_db.link:
                m = DOI_PATT.search(bibitemlink_db.link)
                if m:
                    given_doi = m.group(0)
        if not arxiv_api_success and given_doi:
            try:
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
            except:
                pass
        if not (arxiv_api_success or doi_success):
            text_orig = text.replace('¦', '')
            if 'Phys. Rev.' in text_orig:
                num_phys_rev += 1
            # text = clean_by_segments(text)
            # text = remove_name_list(text)
            # text = remove_containing_work(text)
            text = parscit_get_title(text_orig)
            if not text:
                num_no_title += 1
                continue

        q = title_query_words_simple(text)
        if not q:
            continue
        # print('- - - - - - - - - - - - - - - - -')
        # print(text)
        solr_resps = send_query(q)

        if solr_resps:
            for resp_idx in range(len(solr_resps)):
                candidate = solr_resps[resp_idx]
                solr_match = check_result(text_orig, candidate)
                if solr_match:
                    # print('-> matched at result pos. #{}'.format(resp_idx+1))
                    solr_resp = candidate
                    break
        else:
            solr_match = False
            if arxiv_api_success:
                num_by_aid_fail += 1
        if not solr_match:
            solr_resp = False
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
                mag_id_db = BibitemMAGIDMap(
                    uuid=bibitem_db.uuid,
                    mag_id=mag_id
                    )
                # try to add to DB
                session.begin_nested()
                try:
                    session.add(mag_id_db)
                    session.flush()
                except IntegrityError:
                    # duplicate link
                    session.rollback()
                session.commit()
            result_doi = solr_resp.get('doi', False)
            if given_doi and result_doi:
                num_checked += 1
                if not given_doi == result_doi:
                    num_false_positives += 1
                    # print('identified {}'.format(result_doi))
                    # print('but should\'ve been {}'.format(given_doi))
                    # input()
        t2 = datetime.datetime.now()
        d = t2 - t1
        # print('- - - [{}.{} s] - - -'.format(d.seconds, d.microseconds))
        # print('enter to continue')
        # input()
        print('- - - - - - - - - - - - - - - - -')
        print('{}/{}'.format(bi_idx+1, bi_total))
        print('matches: {}'.format(num_matches))
        print('checked: {}'.format(num_checked))
        print('Phys. Rev.: {}'.format(num_phys_rev))
        print('no title: {}'.format(num_no_title))
        print('false positives: {}'.format(num_false_positives))
        print('by arXiv ID: {}'.format(num_by_aid))
        print('by arXiv ID fail: {}'.format(num_by_aid_fail))
        print('by doi: {}'.format(num_by_doi))
    session.commit()


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
