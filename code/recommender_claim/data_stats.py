""" Generate stats for a parsed and matched arXiv dump
"""

import json
import os
import re
import requests
import sys
import string
from lxml import etree
from sqlalchemy import create_engine
from db_model import Base, Bibitem, BibitemArxivIDMap


def mag_paper_fos(db_engine, mid):
    tuples = db_engine.execute(
        ('select normalizedname from fieldsofstudy join paperfieldsofstudy on '
         'fieldsofstudy.fieldofstudyid = paperfieldsofstudy.fieldofstudyid '
         'where paperid = {} and level = 0').format(mid)
        ).fetchall()
    return [t[0] for t in tuples]


def get_arxiv_fos_web(aid):
    base_url = 'http://export.arxiv.org/api/query?search_query=id:'
    namespaces = {'atom': 'http://www.w3.org/2005/Atom',
                  'opensearch': 'http://a9.com/-/spec/opensearch/1.1/'}

    resp = requests.get('{}{}&start=0&max_results=1'.format(base_url, aid))
    if resp.status_code != 200:
        return None
    xml_root = etree.fromstring(resp.text.encode('utf-8'))
    num_result_elems = xml_root.xpath('/atom:feed/opensearch:totalResults',
                                      namespaces=namespaces)
    num_results = int(num_result_elems[0].text)
    if num_results < 1:
        return None
    result_elems = xml_root.xpath('/atom:feed/atom:entry',
                                  namespaces=namespaces)
    res_elem = result_elems[0]
    fos_elem = res_elem.find('{http://arxiv.org/schemas/atom}primary_category')
    return fos_elem.get('term')


def get_arxiv_fos_db(aid, db_engine):
    tpl = db_engine.execute(
        'select fos from paper where aid  = \'{}\''.format(aid)
        ).fetchone()
    if tpl and len(tpl) > 0:
        return tpl[0]
    else:
        return 'other'

def in_doc_to_aid(in_doc):
    aid = in_doc
    if re.search('[a-z]', in_doc, re.I):
        m = re.search('[a-z][0-9]', in_doc, re.I)
        cut = m.start() + 1
        aid = '{}/{}'.format(in_doc[:cut], in_doc[cut:])
    return aid


def generate(in_dir, db_uri=None):
    """ Generate stats

        If no db_uri is given, a SQLite file metadata.db is expected in in_dir.
    """

    if not db_uri:
        db_path = os.path.join(in_dir, 'metadata.db')
        db_uri = 'sqlite:///{}'.format(os.path.abspath(db_path))
    engine = create_engine(db_uri)

    mag_db_uri = 'postgresql+psycopg2://mag:1maG$@localhost:5432/MAG'
    mag_engine = create_engine(mag_db_uri,
        connect_args={'options': '-c statement_timeout=60000'}
        )

    aid_db_uri = 'sqlite:///aid_fos.db'
    aid_engine = create_engine(aid_db_uri, connect_args={'timeout': 60})

    print('querying DB')
    q = ('select bibitem.uuid, mag_id, in_doc'
         ' from bibitemmagidmap join bibitem'
         ' on bibitemmagidmap.uuid = bibitem.uuid'
         ' order by mag_id');
    tuples = engine.execute(q).fetchall()
    print('going through {} citing docs'.format(len(tuples)))
    tuple_idx = 0
    mag_id = tuples[0][1]
    bag_mag_id = mag_id
    num_citing_docs_total = 0
    nums_citing_docs_per_cited_doc = []
    num_contexts_total = 0
    nums_contexts_per_citing_doc = []
    cited_docs_per_fos = {}
    citing_docs_per_fos = {}
    citation_fos_pairs = []
    while tuple_idx < len(tuples):
        tmp_list = []
        num_citing_docs = 0
        fos_added = False
        while mag_id == bag_mag_id and tuple_idx < len(tuples):
            if tuple_idx % 1000 == 0:
                print('{}/{}'.format(tuple_idx, len(tuples)))
                print('num_citing_docs_total: {}'.format(num_citing_docs_total))
                print('num_contexts_total: {}'.format(num_contexts_total))
                print('cited_docs_per_fos:')
                for k, v in cited_docs_per_fos.items():
                    print('  {}: {}'.format(k, v))
                print('citing_docs_per_fos:')
                for k, v in citing_docs_per_fos.items():
                    print('  {}: {}'.format(k, v))
            uuid = tuples[tuple_idx][0]
            in_doc = tuples[tuple_idx][2]
            fn_txt = '{}.txt'.format(in_doc)
            path_txt = os.path.join(in_dir, fn_txt)
            if not os.path.isfile(path_txt):
                tuple_idx += 1
                continue
            with open(path_txt) as f:
                text = f.read()
            marker = '{{{{cite:{}}}}}'.format(uuid)
            num_contexts = 0
            for m in re.finditer(marker, text):
                num_contexts += 1
            if num_contexts == 0:
                tuple_idx += 1
                continue
            # everything in order, do stats from here
            num_citing_docs_total += 1
            num_contexts_total += num_contexts
            num_citing_docs += 1
            nums_contexts_per_citing_doc.append(num_contexts)
            tuple_idx += 1
            if tuple_idx < len(tuples):
                mag_id = tuples[tuple_idx][1]
            if not fos_added:
                # cited
                foss = mag_paper_fos(mag_engine, mag_id)
                for fos in foss:
                    if fos not in cited_docs_per_fos:
                        cited_docs_per_fos[fos] = 0
                    cited_docs_per_fos[fos] += 1
                # citing
                aid = in_doc_to_aid(in_doc)
                arxiv_fos = get_arxiv_fos_db(aid, aid_engine)
                if arxiv_fos:
                    if not arxiv_fos in citing_docs_per_fos:
                        citing_docs_per_fos[arxiv_fos] = 0
                    citing_docs_per_fos[arxiv_fos] += 1
                    if len(foss) > 0:
                        citation_fos_pairs.append((arxiv_fos, foss[0]))
                fos_added = True
        nums_citing_docs_per_cited_doc.append(num_citing_docs)
        if tuple_idx < len(tuples):
            bag_mag_id = tuples[tuple_idx][1]
    print('{}/{}'.format(tuple_idx, len(tuples)))
    print('num_citing_docs_total: {}'.format(num_citing_docs_total))
    print('num_contexts_total: {}'.format(num_contexts_total))
    print('cited_docs_per_fos:')
    for k, v in cited_docs_per_fos.items():
        print('  {}: {}'.format(k, v))
    print('citing_docs_per_fos:')
    for k, v in citing_docs_per_fos.items():
        print('  {}: {}'.format(k, v))
    with open('contexts_per_citing_doc.json', 'w') as f:
        f.write(json.dumps(nums_contexts_per_citing_doc))
    with open('citing_docs_per_cited_doc.json', 'w') as f:
        f.write(json.dumps(nums_citing_docs_per_cited_doc))
    with open('citation_fos_pairs.json', 'w') as f:
        f.write(json.dumps(citation_fos_pairs))

if __name__ == '__main__':
    if len(sys.argv) not in [2, 3]:
        print(('usage: python3 generate_dataset.py </path/to/in/dir> [<db_uri>'
               ']'))
        sys.exit()
    in_dir = sys.argv[1]
    if len(sys.argv) == 3:
        db_uri = sys.argv[2]
        ret = generate(in_dir, db_uri=db_uri)
    else:
        ret = generate(in_dir)
    if not ret:
        sys.exit()
