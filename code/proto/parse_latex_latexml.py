""" convert latex files to plain text with nice citation markers

    TODO:
        - do sth. w/ white space caused by e.g. tables (?)
        - plan B for latexml fails? (e.g. preable cleaning)
        - SPEEDUP (currently ~10s per doc)
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import uuid
from lxml import etree

if len(sys.argv) != 3:
    print(('usage: python3 parse_latex_latexml.py </path/to/in/dir> </path/to/'
           'out/dir>'))
    sys.exit()

IN_DIR = sys.argv[1]
OUT_DIR = sys.argv[2]
PDF_EXT_PATT = re.compile(r'^\.pdf$', re.I)


def log(msg):
    with open(os.path.join(OUT_DIR, 'log.txt'), 'a') as f:
        f.write('{}\n'.format(msg))


if not os.path.isdir(IN_DIR):
    print('input directory does not exist')
    sys.exit()

if not os.path.isdir(OUT_DIR):
    os.makedirs(OUT_DIR)

for fn in os.listdir(IN_DIR):
    path = os.path.join(IN_DIR, fn)
    aid, ext = os.path.splitext(fn)
    print(aid)
    if PDF_EXT_PATT.match(ext):
        log('skipping file {}'.format(fn))
        continue

    with tempfile.TemporaryDirectory() as tmp_dir_path:
        tmp_xml_path = os.path.join(tmp_dir_path, 'out.xml')
        # run latexml
        latexml_args = ['latexml',
                        '--nocomments',
                        '--destination={}'.format(tmp_xml_path),
                        path]

        out = open(tmp_xml_path, mode='w')
        err = open(os.path.join(OUT_DIR, 'log_latexml.txt'), 'a')
        err.write('\n------------- {} -------------\n'.format(aid))
        err.flush()
        subprocess.run(latexml_args, stdout=out, stderr=err, timeout=60)
        out.close()
        err.close()

        # get mathless plain text from latexml output
        parser = etree.XMLParser()
        with open(tmp_xml_path) as f:
            try:
                tree = etree.parse(f, parser)
            except etree.XMLSyntaxError as e:
                print('FAILED {}. skipping'.format(aid))
                log('\n--- {} ---\n{}\n----------\n'.format(fn, e))
                continue
        etree.strip_elements(tree,
                             '{http://dlmf.nist.gov/LaTeXML}equationgroup',
                             with_tail=False)
        etree.strip_elements(tree,
                             '{http://dlmf.nist.gov/LaTeXML}equation',
                             with_tail=False)
        etree.strip_elements(tree,
                             '{http://dlmf.nist.gov/LaTeXML}Math',
                             with_tail=False)

        # processing of citation markers
        namespaces = {'LaTeXML': 'http://dlmf.nist.gov/LaTeXML'}
        bibitems = tree.xpath('//LaTeXML:bibitem', namespaces=namespaces)
        bibkey_map = {}
        bibitem_map = {}

        for bi in bibitems:
            uid = str(uuid.uuid4())
            local_key = bi.get('key')
            bibkey_map[local_key] = uid
            etree.strip_elements(bi, '{http://dlmf.nist.gov/LaTeXML}bibtag')
            text = etree.tostring(bi, encoding='unicode', method='text')
            text = re.sub('\s+', ' ', text).strip()
            bibitem_map[uid] = text

        citations = tree.xpath('//LaTeXML:cite', namespaces=namespaces)
        for cit in citations:
            elem = cit.find('{http://dlmf.nist.gov/LaTeXML}bibref')
            sep = elem.get('separator')
            refs_list = elem.get('bibrefs')
            if refs_list:
                refs = refs_list.split(sep)
            else:
                refs = []
            replace_text = ''
            for ref in refs:
                if ref in bibkey_map:
                    marker = '{{{{cite:{}}}}}'.format(bibkey_map[ref])
                    replace_text += marker
                else:
                    log(('WARNING: unmatched bibliography key {} for doc {}'
                         '').format(ref, aid))
            if cit.tail:
                cit.tail = replace_text + cit.tail
            else:
                cit.tail = replace_text
        # /processing of citation markers
        etree.strip_elements(tree,
                             '{http://dlmf.nist.gov/LaTeXML}cite',
                             with_tail=False)
        etree.strip_elements(tree,
                             '{http://dlmf.nist.gov/LaTeXML}bibliography',
                             with_tail=False)
        etree.strip_elements(tree,
                             '{http://dlmf.nist.gov/LaTeXML}biblist',
                             with_tail=False)
        etree.strip_elements(tree,
                             '{http://dlmf.nist.gov/LaTeXML}bibitem',
                             with_tail=False)
        etree.strip_tags(tree, '*')
        tree_str = etree.tostring(tree, encoding='unicode', method='text')

        out_txt_path = os.path.join(OUT_DIR, '{}.txt'.format(aid))
        out_map_path = os.path.join(OUT_DIR, '{}_map.json'.format(aid))
        with open(out_txt_path, 'w') as f:
            f.write(tree_str)
        with open(out_map_path, 'w') as f:
            f.write(json.dumps(bibitem_map))
