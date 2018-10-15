""" convert a latex file to plain text with nice citation markers

    TODO:
        - do sth. w/ white space caused by e.g. tables (?)
"""

import json
import os
import re
import subprocess
import sys
import uuid
from lxml import etree

IN_FILE = sys.argv[1]
OUT_DIR = '/tmp'
latexml_tmp = 'out.xml'

# run latexml
latexml_args = ['latexml',
                '--nocomments',
                '--destination={}'.format(latexml_tmp),
                IN_FILE]

out = open(latexml_tmp, mode='w')
err = open(os.path.join(OUT_DIR, 'log_latexml.txt'), 'a')
err.write('\n------------- {} -------------\n'.format(IN_FILE))
err.flush()
subprocess.run(latexml_args, stdout=out, stderr=err)
out.close()
err.close()

# get mathless plain text from latexml output
parser = etree.XMLParser()
with open(latexml_tmp) as f:
    tree = etree.parse(f, parser)
etree.strip_elements(tree, '{http://dlmf.nist.gov/LaTeXML}equationgroup', with_tail=False)
etree.strip_elements(tree, '{http://dlmf.nist.gov/LaTeXML}equation', with_tail=False)
etree.strip_elements(tree, '{http://dlmf.nist.gov/LaTeXML}Math', with_tail=False)
# processing of citation markers

namespaces = {'LaTeXML':'http://dlmf.nist.gov/LaTeXML'}
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
    refs = elem.get('bibrefs').split(sep)
    replace_text = ''
    for ref in refs:
        if ref in bibkey_map:
            marker = '{{{{cite:{}}}}}'.format(bibkey_map[ref])
            replace_text += marker
        else:
            print(('WARNING: unmatched bibliography key {}'
                   '').format(ref))
    cit.tail = replace_text + cit.tail

# /processing of citation markers
etree.strip_elements(tree, '{http://dlmf.nist.gov/LaTeXML}cite', with_tail=False)
etree.strip_elements(tree, '{http://dlmf.nist.gov/LaTeXML}bibliography', with_tail=False)
etree.strip_elements(tree, '{http://dlmf.nist.gov/LaTeXML}biblist', with_tail=False)
etree.strip_elements(tree, '{http://dlmf.nist.gov/LaTeXML}bibitem', with_tail=False)
etree.strip_tags(tree, '*')
tree_str = etree.tostring(tree, encoding='unicode', method='text')

with open('out.txt', 'w') as f:
    f.write(tree_str)
with open('map.json', 'w') as f:
    f.write(json.dumps(bibitem_map))
