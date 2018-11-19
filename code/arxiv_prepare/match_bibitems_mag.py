""" Match bibitem strings to MAG IDs

    TODO:
        - strip "(in) Proceedings)" etc. (Proceedings themselves
          are in MAG)
        - if there's a DOI, get MAG ID by DOI
        - if false positives too high (after stipping Proceedings
          etc.), check authors
"""

import datetime
import os
import re
import requests
import sys
from random import shuffle
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from db_model import (Base, Bibitem, BibitemArxivIDMap, BibitemMAGIDMap,
                      BibitemLinkMap)

DOI_PATT = re.compile(r'10.\d{4,9}/[-._;()/:A-Z0-9]+$', re.I)


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
    return docs[:10]


def clean(s):
    s = re.sub('[^\w\s]+', '', s)
    s = re.sub('\s+', ' ', s)
    return s.strip().lower()

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

    bibitems_db = session.query(Bibitem).all()
    shuffle(bibitems_db)
    num_matches = 0
    num_checked = 0
    num_false_positives = 0
    num_false_negatives = 0
    bi_total = len(bibitems_db)
    for bi_idx, bibitem_db in enumerate(bibitems_db):
        t1 = datetime.datetime.now()
        text = bibitem_db.bibitem_string
        in_doc = bibitem_db.in_doc
        text = text.replace('¦', '')

        q = title_query_words(text)
        if not q:
            continue
        # print('- - - - - - - - - - - - - - - - -')
        # print(text)
        solr_resps = send_query(q)
        
        if solr_resps:
            for resp_idx in range(len(solr_resps)):
                candidate = solr_resps[resp_idx]
                solr_match = check_result(text, candidate)
                if solr_match:
                    # print('-> matched at result pos. #{}'.format(resp_idx+1))
                    solr_resp = candidate
                    break
        else:
            solr_match = False
        if not solr_match:
            solr_resp = False
            
        # if not solr_match:
        #     print('-> no match')

        # input()
        # continue

        given_link_db = session.query(BibitemLinkMap).filter_by(
                                      uuid=bibitem_db.uuid).first()
        given_doi = False
        if given_link_db:
            if 'doi' in given_link_db.link:
                m = DOI_PATT.search(given_link_db.link)
                if m:
                    given_doi = m.group(0)

        if given_doi:
            num_checked += 1
        if not solr_match:
            if given_doi:
                num_false_negatives += 1
            continue
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
            if given_doi and result_doi and not given_doi == result_doi:
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
        print('false negatives: {}'.format(num_false_negatives))
        print('false positives: {}'.format(num_false_positives))
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