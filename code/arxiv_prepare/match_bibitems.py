import datetime
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
    base_url = 'http://export.arxiv.org/api/query?search_query=all:'
    namespaces = {'atom': 'http://www.w3.org/2005/Atom',
                  'opensearch': 'http://a9.com/-/spec/opensearch/1.1/'}

    for bibitem_db in bibitems_db:
        text = bibitem_db.bibitem_string
        print('Text: {}'.format(text))
        clean_text = re.sub('[^a-zA-Z0-9\s]+', ' ', text)
        years = [w for w in clean_text.split(' ') if w in feasible_years]
        cleaner_text = re.sub('[0-9]+', '', clean_text)
        words = [w for w in cleaner_text.split(' ') if
                 len(w) > 2 and w not in stop_words]
        query = ' '.join(words + years)
        print('Query: {}'.format(query))
        resp = requests.get('{}{}&start=0&max_results=10'.format(base_url,
                                                                 query))
        if resp.status_code != 200:
            print('unexpected API response: {}\n{}'.format(resp.status_code,
                                                           resp.text))
            print('enter to continue')
            input()
            continue
        xml_root = etree.fromstring(resp.text.encode('utf-8'))
        num_result_elems = xml_root.xpath('/atom:feed/opensearch:totalResults',
                                          namespaces=namespaces)
        num_results = int(num_result_elems[0].text)
        if num_results < 1:
            print('no results')
            print('enter to continue')
            input()
            continue
        result_elems = xml_root.xpath('/atom:feed/atom:entry',
                                      namespaces=namespaces)
        for res_elem in result_elems:
            aid = res_elem.find('{http://www.w3.org/2005/Atom}id').text
            title = res_elem.find('{http://www.w3.org/2005/Atom}title').text
            print('Found: {} ({})'.format(title, aid))
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
