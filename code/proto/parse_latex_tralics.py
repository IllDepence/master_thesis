""" convert latex files to plain text with nice citation markers
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
    print(('usage: python3 parse_latex_tralics.py </path/to/in/dir> </path/to/'
           'out/dir>'))
    sys.exit()

INCREMENTAL = True
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
    out_txt_path = os.path.join(OUT_DIR, '{}.txt'.format(aid))
    if INCREMENTAL and os.path.isfile(out_txt_path):
        print('{} already in output directory, skipping'.format(aid))
        continue
    print(aid)
    if PDF_EXT_PATT.match(ext):
        log('skipping file {} (PDF)'.format(fn))
        continue

    with tempfile.TemporaryDirectory() as tmp_dir_path:
        tmp_xml_path = os.path.join(tmp_dir_path, '{}.xml'.format(aid))
        # run latexml
        tralics_args = ['tralics',
                        '-silent',
                        '-noxmlerror',
                        '-utf8',
                        '-oe8',
                        '-entnames=false',
                        '-nomathml',
                        '-output_dir={}'.format(tmp_dir_path),
                        path]

        out = open(os.path.join(OUT_DIR, 'tralics_out.txt'), mode='w')
        err = open(os.path.join(OUT_DIR, 'log_tralics.txt'), 'a')
        err.write('\n------------- {} -------------\n'.format(aid))
        err.flush()
        try:
            subprocess.run(tralics_args, stdout=out, stderr=err, timeout=60)
        except subprocess.TimeoutExpired as e:
            print('FAILED {}. skipping'.format(aid))
            log('\n--- {} ---\n{}\n----------\n'.format(aid, e))
            continue
        out.close()
        err.close()

        # get mathless plain text from latexml output
        parser = etree.XMLParser()
        with open(tmp_xml_path) as f:
            try:
                tree = etree.parse(f, parser)
            except etree.XMLSyntaxError as e:
                print('FAILED {}. skipping'.format(aid))
                log('\n--- {} ---\n{}\n----------\n'.format(aid, e))
                continue
        etree.strip_elements(tree, 'formula', with_tail=False)

        # processing of citation markers
        bibitems = tree.xpath('//bibitem')
        bibkey_map = {}
        bibitem_map = {}

        for bi in bibitems:
            uid = str(uuid.uuid4())
            local_key = bi.get('id')
            bibkey_map[local_key] = uid
            containing_p = bi.getparent()
            text = etree.tostring(containing_p,
                                  encoding='unicode',
                                  method='text')
            text = re.sub('\s+', ' ', text).strip()
            bibitem_map[uid] = text

        citations = tree.xpath('//cit')
        for cit in citations:
            elem = cit.find('ref')
            if elem is None:
                log(('WARNING: cite element in {} contains no ref element'
                     '').format(aid))
                continue
            ref = elem.get('target')
            replace_text = ''
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
        etree.strip_elements(tree, 'Bibliography', with_tail=False)
        etree.strip_elements(tree, 'bibitem', with_tail=False)
        etree.strip_elements(tree, 'cit', with_tail=False)
        etree.strip_tags(tree, '*')
        tree_str = etree.tostring(tree, encoding='unicode', method='text')

        out_map_path = os.path.join(OUT_DIR, '{}_map.json'.format(aid))
        with open(out_txt_path, 'w') as f:
            f.write(tree_str)
        with open(out_map_path, 'w') as f:
            f.write(json.dumps(bibitem_map))
