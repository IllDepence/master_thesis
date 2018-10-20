import datetime
import json
import os
import re
import requests
import sys
from lxml import etree
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_model import Base, Bibitem, BibitemArxivIDMap

def match(db_uri=None, in_dir=None):
    if not (db_uri or in_dir):
        print('need either DB URI or input directory path')
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
    base_url = 'http://localhost:8983/solr/arxiv_meta/select?q='

    namespaces = {'atom': 'http://www.w3.org/2005/Atom',
                  'opensearch': 'http://a9.com/-/spec/opensearch/1.1/'}

    for bibitem_db in bibitems_db:
        t1 = datetime.datetime.now()
        text = bibitem_db.bibitem_string
        print('Text: {}'.format(text))
        clean_text = re.sub('[^\w\s]+', ' ', text)
        years = [w for w in clean_text.split(' ') if w in feasible_years]
        cleaner_text = re.sub('[0-9]+', '', clean_text)
        words = [w for w in cleaner_text.split(' ') if
                 len(w) > 2 and w not in stop_words]
        query = '%2B'.join(words + years)
        resp = requests.get(('{0}title:{1}%20AND%20creator:{1}&rows=1&wt=json'
                             '').format(base_url, query))
        if resp.status_code != 200:
            print('unexpected API response: {}\n{}'.format(resp.status_code,
                                                           resp.text))
            print('enter to continue')
            input()
            continue
        resp_json = resp.json()
        num_results = resp_json.get('response', {}).get('numFound', 0)
        if num_results < 1:
            print('no results')
            print('enter to continue')
            input()
            continue
        doc = resp_json.get('response', {}).get('docs', [{}])[0]
        title = doc.get('title', [''])[0]
        creator = '; '.join(doc.get('creator', ['']))
        print('Found: {} ({})'.format(title, creator))
        t2 = datetime.datetime.now()
        d = t2 - t1
        print('- - - [{}.{} s] - - -'.format(d.seconds, d.microseconds))
        print('enter to continue')
        input()

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
