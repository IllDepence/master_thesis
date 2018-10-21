""" Match bibitem strings to arXiv IDs

    TODO:
        - look through should've matched items
        - generate stats of coverage by complete run
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
from db_model import Base, Bibitem, BibitemArxivIDMap

ARXIV_URL_PATT = re.compile(
    r'arxiv\.org\/[a-z0-9]{1,10}\/(([a-z0-9-]{1,15}\/)?[\d\.]{5,10}(v\d)?$)',
    re.I)
PROCEEDINGS_TAIL_PATT = re.compile(r'.{10,}Proceedings of', re.I)
PROCEEDINGS_START_PATT = re.compile(r'^\s*(in)?\s*Proceedings of', re.I)
JOURNAL_OF_PATT = re.compile(r'Journal of', re.I)
IN_START_PATT = re.compile(r'^\s*in\s+', re.I)
PAGE_PATT = re.compile(r'pages?\s*:?\s*\d+', re.I)
IN_X_START_PATT = re.compile(
    r'^\s*(in)?\s*(the)?\s*(Proceedings|Journal)\s+of', re.I)
TRANSACTIONS_START_PATT = re.compile(
    r'^\s*\w+?\s*(Transactions)\s+on', re.I)
IN_X_DELIM_PATT = re.compile(
    r'(,|\.|;)\s*(in)?\s*(the)?\s*(Proceedings|Journal)\s+of', re.I)
VOLUME_DELIM_PATT = re.compile(r'(,|\.|;)\s*Volume\s+\d+', re.I)


def send_query(query):
    base_url = 'http://localhost:8983/solr/arxiv_meta/select?q='
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
    # print('Top 5 results:')
    # for doc in docs[:5]:
    #     print('        - {}'.format(doc.get('title', [''])[0]))
    return docs[0]


def clean(s):
    s = re.sub('[^\w\s]+', '', s)
    s = re.sub('\s+', ' ', s)
    return s.strip().lower()


def check_result(bibitem_string, result_doc, debug=False):
    clean_orig = clean(bibitem_string)
    clean_result_title = clean(result_doc.get('title', [''])[0])
    creators = result_doc.get('creator', [])
    clean_creators = [clean(c) for c in creators]
    # check for author match
    one_valid_author = False
    for cc in clean_creators:
        if one_valid_author:
            break
        names = cc.split(' ')
        for name in names:
            if one_valid_author:
                break
            name = name.strip()
            if len(name) < 2 or name in ['et', 'al', 'and']:
                continue
            if name in clean_orig:
                one_valid_author = True
    if debug:
        print('any of: {}\nin\n{}\n→{}'.format(clean_creators, clean_orig,
                                               one_valid_author))
    if not one_valid_author:
        return False
    # check for exact title match
    exact_title = clean_result_title in clean_orig
    if debug:
        print('{}\nin\n{}\n→{}'.format(clean_result_title, clean_orig,
                                       exact_title))
    if exact_title:
        return True
    # check for good enough title match
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
        found_ratio = len(needles) / found_count
    except ZeroDivisionError:
        found_ratio = 0
    try:
        order_ratio = found_count / correct_order_count
    except ZeroDivisionError:
        order_ratio = 0
    if debug:
        print('found ratio: {}\norder ratio: {}'.format(found_ratio,
                                                        order_ratio))
    return found_ratio > 0.67 and order_ratio > 0.8


def guess_delimiter(text):
    delim = '.'
    match = IN_X_DELIM_PATT.search(text)
    if match:
        delim =  match.group(1)
    match = VOLUME_DELIM_PATT.search(text)
    if match:
        delim =  match.group(1)
    return delim


def title_by_length_and_exclusion(text):
    """ Assumption: excluding the journal/proceedings/etc. part, the title is
                    the longest part
    """

    delim = guess_delimiter(text)
    title_candidates = text.split(delim)
    longest = ''
    second = ''
    for tc in title_candidates:
        tc = tc.strip()
        if PROCEEDINGS_START_PATT.search(tc):
            continue
        if JOURNAL_OF_PATT.search(tc):
            continue
        if PAGE_PATT.search(tc):
            continue
        if PROCEEDINGS_TAIL_PATT.search(tc):
            tc = tc.split('Proceedings')[0]
            tc = tc.split('proceedings')[0]
        if len(tc) > len(longest):
            second = longest
            longest = tc
    if IN_START_PATT.search(longest) and not IN_START_PATT.search(second):
        longest = second
    return longest


def title_by_succeeding_string(text):
    """ Assumption: the journal/proceedings/etc. part is the most regular (i.e.
                    easiest to identify) and immediately follows the title
    """

    delim = guess_delimiter(text)
    title_candidates = text.split(delim)
    title_guess = None
    prior = None
    for tc in title_candidates:
        if IN_X_START_PATT.search(tc) or \
                TRANSACTIONS_START_PATT.search(tc) or \
                PAGE_PATT.search(tc):
            title_guess = prior
            break
        prior = tc
    if not title_guess:
        return title_by_length_and_exclusion(text)
    return title_guess


def match(db_uri=None, in_dir=None):
    if not (db_uri or in_dir):
        # print('need either DB URI or input directory path')
        return False
    with open('stopwords.txt') as f:
        stop_lines = f.readlines()
    stop_words = [line.strip() for line in stop_lines]
    current_year = datetime.datetime.today().year
    # https://en.wikipedia.org/wiki/Scientific_journal#History
    feasible_years = list(range(1665, current_year+1, 1))
    feasible_years = [str(y) for y in feasible_years]
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
    num_obv_misses = 0
    for bibitem_db in bibitems_db:
        t1 = datetime.datetime.now()
        text = bibitem_db.bibitem_string
        in_doc = bibitem_db.in_doc
        # print('--------------- {} ---------------'.format(in_doc))
        # print('Text:           {}'.format(text))

        # try to find match by title
        title_guess = title_by_succeeding_string(text)
        # title_guess = title_by_length_and_exclusion(text)
        # print('Title guess:    {}'.format(title_guess))
        if len(title_guess) == 0:
            continue
        author_str = text.split(title_guess)[0]
        author_str = re.sub('[^\w\s]+', ' ', author_str)
        author_strs = [s for s in author_str.split(' ') if len(s) > 2]
        # print('Author strings: {}'.format(' '.join(author_strs)))
        doc = send_query('title:"{}"'.format(title_guess))
        if doc:
            m = check_result(text, doc)
        else:
            m = False
        if not m:
            # print('>>>> 2nd try >>>>')
            clean_text = re.sub('[^\w\s]+', ' ', text)
            years = [w for w in clean_text.split(' ') if w in feasible_years]
            cleaner_text = re.sub('[0-9]+', '', clean_text)
            words = [w for w in cleaner_text.split(' ') if
                     len(w) > 2 and w not in stop_words]
            query_string = '%2B'.join(words + years)
            query = ('title:{0}%20AND%20creator:{0}'
                     '&rows=1&wt=json').format(query_string)
            doc = send_query('title:"{}"'.format(title_guess))
            if not doc:
                # print('enter to continue')
                # input()
                continue
            m = check_result(text, doc)
            if not m:
                # print('No match.')
                for idf in doc.get('identifier', []):
                    if ARXIV_URL_PATT.search(idf):
                        num_obv_misses += 1
                        # print(('####################\nBUT SHOULD HAVE MATCHED:'
                        #        ' {} ({})\n####################'
                        #        '').format(doc.get('title', [''])[0], idf))
                # print('enter to continue')
                # input()
                continue
        if m:
            num_matches += 1
        # title = doc.get('title', [''])[0]
        # creator = '; '.join(doc.get('creator', ['']))
        # print('Found: {} ({})'.format(title, creator))
        t2 = datetime.datetime.now()
        d = t2 - t1
        # print('- - - [{}.{} s] - - -'.format(d.seconds, d.microseconds))
        # print('enter to continue')
        # input()
    print('total: {}'.format(len(bibitems_db)))
    print('matches: {}'.format(num_matches))
    print('obv. misses: {}'.format(num_obv_misses))

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
