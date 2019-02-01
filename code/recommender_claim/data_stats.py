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
    print('generating aid FoS map')
    tpls = aid_engine.execute(
        'select aid, fos from paper'
        ).fetchall()
    aid_fos_map = {}
    for tpl in tpls:
        aid_fos_map[tpl[0]] = tpl[1]

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
    num_reference_items_total = 0
    citing_docs = set()
    citing_docs_cs = set()
    citing_docs_phys = set()
    citing_docs_math = set()
    citing_docs_other = set()
    cited_docs = set()
    nums_reference_items_per_cited_doc = []
    num_contexts_total = 0
    nums_contexts_per_referece = []
    cited_docs_per_fos = {}
    reference_items_per_fos = {}
    citation_fos_pairs = []
    while tuple_idx < len(tuples):
        tmp_list = []
        num_reference_items = 0
        cited_fos_added = False
        foss = []
        while mag_id == bag_mag_id and tuple_idx < len(tuples):
            if tuple_idx % 1000 == 0:
                print('{}/{}'.format(tuple_idx, len(tuples)))
                print('num_reference_items_total: {}'.format(num_reference_items_total))
                print('num_citing_docs_total: {}'.format(len(citing_docs)))
                # print('num_cited_docs_total: {}'.format(len(cited_docs)))
                print('num_contexts_total: {}'.format(num_contexts_total))
                print('cited_docs_per_fos:')
                for k, v in cited_docs_per_fos.items():
                    print('  {}: {}'.format(k, v))
                print('reference_items_per_fos:')
                for k, v in reference_items_per_fos.items():
                    print('  {}: {}'.format(k, v))
                print('num_citation_pairs_total: {}'.format(
                    len(citation_fos_pairs))
                    )
                print('citing_docs_cs: {}'.format(len(citing_docs_cs)))
                print('citing_docs_math: {}'.format(len(citing_docs_math)))
                print('citing_docs_phys: {}'.format(len(citing_docs_phys)))
                print('citing_docs_other: {}'.format(len(citing_docs_other)))
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
            # cited_docs.add(mag_id)
            # citing_docs.add(in_doc)
            num_reference_items_total += 1
            num_contexts_total += num_contexts
            num_reference_items += 1
            nums_contexts_per_referece.append(num_contexts)
            if not cited_fos_added:
                # cited doc level
                foss = mag_paper_fos(mag_engine, mag_id)
                if len(foss) == 0:
                    foss = ['other']
                for fos in foss:
                    if fos not in cited_docs_per_fos:
                        cited_docs_per_fos[fos] = 0
                    cited_docs_per_fos[fos] += 1
                cited_fos_added = True
            # reference level
            aid = in_doc_to_aid(in_doc)
            arxiv_fos = aid_fos_map.get(aid, 'other')
            if not arxiv_fos in reference_items_per_fos:
                reference_items_per_fos[arxiv_fos] = 0
            reference_items_per_fos[arxiv_fos] += 1
            if arxiv_fos == 'cs':
                citing_docs_cs.add(aid)
            elif arxiv_fos == 'math':
                citing_docs_math.add(aid)
            elif 'physics' in arxiv_fos:
                citing_docs_phys.add(aid)
            else:
                citing_docs_other.add(aid)
            citation_fos_pairs.append((arxiv_fos, foss[0]))
            # end
            tuple_idx += 1
            if tuple_idx < len(tuples):
                mag_id = tuples[tuple_idx][1]
        nums_reference_items_per_cited_doc.append(num_reference_items)
        if tuple_idx < len(tuples):
            bag_mag_id = tuples[tuple_idx][1]
    print('{}/{}'.format(tuple_idx, len(tuples)))
    print('num_reference_items_total: {}'.format(num_reference_items_total))
    print('num_citing_docs_total: {}'.format(len(citing_docs)))
    print('num_cited_docs_total: {}'.format(len(cited_docs)))
    print('num_contexts_total: {}'.format(num_contexts_total))
    print('cited_docs_per_fos:')
    for k, v in cited_docs_per_fos.items():
        print('  {}: {}'.format(k, v))
    print('reference_items_per_fos:')
    for k, v in reference_items_per_fos.items():
        print('  {}: {}'.format(k, v))
    print('citing_docs_cs: {}'.format(len(citing_docs_cs)))
    print('citing_docs_math: {}'.format(len(citing_docs_math)))
    print('citing_docs_phys: {}'.format(len(citing_docs_phys)))
    print('citing_docs_other: {}'.format(len(citing_docs_other)))
    # with open('contexts_per_referece.json', 'w') as f:
    #     f.write(json.dumps(nums_contexts_per_referece))
    # with open('reference_items_per_cited_doc.json', 'w') as f:
    #     f.write(json.dumps(nums_reference_items_per_cited_doc))
    with open('citation_fos_pairs_fixed_fixed.json', 'w') as f:
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
