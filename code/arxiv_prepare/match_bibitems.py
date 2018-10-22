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


def send_query(query, debug=False):
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
    if debug:
        print('Top 5 results:')
        for doc in docs[:5]:
            print('        - {}'.format(doc.get('title', [''])[0]))
    return docs[0]


def clean(s):
    s = re.sub('[^\w\s]+', '', s)
    s = re.sub('\s+', ' ', s)
    return s.strip().lower()


def check_result(bibitem_string, result_doc, debug=False):
    """ For a result doc to pass as fitting require that:

            - at least one original author name appears in the bibitem string
            AND
            (
            - the original title is contained in the bibitem string
             OR
            - the bibitem string contains most of the original title's words in
              correct order
            )
    """

    clean_orig = clean(bibitem_string)
    clean_result_title = clean(result_doc.get('title', [''])[0])
    creators = result_doc.get('creator', [])
    clean_creators = [clean(c) for c in creators]
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
    return False
    # check for year match
    # result_date_strs = result_doc.get('date', [''])
    # result_years = []
    # for rds in result_date_strs:
    #     rds = rds.split('T')[0]  # cut time zone if present
    #     try:
    #         year = datetime.datetime.strptime(rds, '%Y-%m-%d').year
    #     except ValueError:
    #         print(rds)
    #         continue
    #     result_years.append(str(year))
    # for ry in result_years:
    #     if debug:
    #         print('{} in\n{}\n→ {}'.format(ry, bibitem_string,
    #                                     ry in bibitem_string))
    #     if ry in bibitem_string:
    #         return True
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


def title_query_split_heuristic(text):
    title_guess = title_by_succeeding_string(text)
    # title_guess = title_by_length_and_exclusion(text)
    # print('Title guess:    {}'.format(title_guess))
    if len(title_guess) == 0:
        return False
    author_str = text.split(title_guess)[0]
    author_str = re.sub('[^\w\s]+', ' ', author_str)
    author_strs = [s for s in author_str.split(' ') if len(s) > 2]
    # print('Author strings: {}'.format(' '.join(author_strs)))
    return 'title:"{}"'.format(title_guess)


def title_author_query_words(text):
    with open('stopwords.txt') as f:
        stop_lines = f.readlines()
    stop_words = [line.strip() for line in stop_lines]
    # current_year = datetime.datetime.today().year
    # # https://en.wikipedia.org/wiki/Scientific_journal#History
    # feasible_years = list(range(1665, current_year+1, 1))
    # feasible_years = [str(y) for y in feasible_years]

    clean_text = re.sub('[^\w\s]+', ' ', text)
    # years = [w for w in clean_text.split(' ') if w in feasible_years]
    cleaner_text = re.sub('[0-9]+', '', clean_text)
    words = [w for w in cleaner_text.split(' ') if
             len(w) > 2 and w not in stop_words]
    query_string = '%2B'.join(words)  #  + years
    return 'title:{0}%20AND%20creator:{0}'.format(query_string)


def match(db_uri=None, in_dir=None):
    if not (db_uri or in_dir):
        # print('need either DB URI or input directory path')
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
    for bibitem_db in bibitems_db:
        t1 = datetime.datetime.now()
        text = bibitem_db.bibitem_string
        in_doc = bibitem_db.in_doc
        # print('--------------- {} ---------------'.format(in_doc))
        # print('Text:           {}'.format(text))

        # tex_seperated_parts = text.split('¦')  # TODO: use (~80% of bibitems)
        # if len(tex_seperated_parts) > 2:
        #     num_tex_seperated_parts += 1
        text = text.replace('¦', '')

        # try to find match by title
        # q = title_query_split_heuristic(text)
        q = title_author_query_words(text)
        if not q:
            # print('enter to continue')
            # input()
            continue
        doc = send_query(q)
        if doc:
            m = check_result(text, doc)
        else:
            m = False
        ids_db = session.query(BibitemArxivIDMap).filter_by(
                    uuid=bibitem_db.uuid).first()
        if ids_db:
            num_checked += 1
        if not m:
            if ids_db:
                num_false_negatives += 1
            # ids_db = session.query(BibitemArxivIDMap).filter_by(
            #         uuid=bibitem_db.uuid).all()
            # print('No match.')
            # if ids_db:
            #         print(('--------------- {} ---------------'
            #                '').format(in_doc))
            #         print('Text: {}'.format(text))
            #         print(('####################\nSHOULD HAVE MATCHE'
            #                'D: {}\n####################'
            #                '').format(id_db.arxiv_id))
            #         doc = send_query(q, debug=True)
            #         if doc:
            #             m = check_result(text, doc, debug=True)
            #         else:
            #             print('no Solr results')
            #         print('enter to continue')
            #         input()
            continue
        if m:
            # print(text)
            # print('- - - - - - - - - - - - - - - - - - - - - - - - -')
            # aid = ''
            # for idf in doc.get('identifier', []):
            #     if ARXIV_URL_PATT.search(idf):
            #         aid = idf
            # creators = '; '.join(doc.get('creator', ['']))
            # dates = ' | '.join(doc.get('date', ['']))
            # print('{} ({})\n{}\n{}'.format(doc.get('title', [''])[0], aid,
            #                            creators, dates))
            # print('\n\n\n')
            # input()
            num_matches += 1
            ids_db = session.query(BibitemArxivIDMap).filter_by(
                        uuid=bibitem_db.uuid).first()
            if ids_db:
                for idf in doc.get('identifier', []):
                    if ARXIV_URL_PATT.search(idf):
                        if not ids_db.arxiv_id in idf:
                            num_false_positives += 1
                            # print('identified {}'.format(idf))
                            # print('but should\'ve been {}'.format(ids_db.arxiv_id))
                            # input()
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
    print('checked: {}'.format(num_checked))
    print('false negatives: {}'.format(num_false_negatives))
    print('false positives: {}'.format(num_false_positives))

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
