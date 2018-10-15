""" convert a latex file to plain text (soon^TM) with nice citation markers

    TODO:
        - citation markers
        - html entities (&#8217;) back to text
        - do sth. w/ white space caused by e.g. tables
        - cutting away of references (?)
"""

import os
import re
import subprocess
import sys
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
# TODO: pre removal processing of citation markers
etree.strip_tags(tree, '*')
tree_str = etree.tostring(tree, encoding='unicode', method='text')

with open('out.txt', 'w') as f:
    f.write(tree_str)
