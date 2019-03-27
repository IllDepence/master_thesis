""" Count citation markers
"""

import os
import re
import sys

CITE_PATT = re.compile((r'\{\{cite:([0-9A-F]{8}-[0-9A-F]{4}-4[0-9A-F]{3}'
                         '-[89AB][0-9A-F]{3}-[0-9A-F]{12})\}\}'), re.I)

in_dir = sys.argv[1]
print('folder: {}'.format(in_dir))
print('ok?')
input()
fns = os.listdir(in_dir)
num_markers = 0
num_files = 0
for idx, fn in enumerate(fns):
    if idx%10000 == 0:
        print('{}/{}'.format(idx, len(fns)))
    nm, ext = os.path.splitext(fn)
    if ext != '.txt':
        continue
    num_files += 1
    fp = os.path.join(in_dir, fn)
    with open(fp) as f:
        text = f.read()
    mtchs = CITE_PATT.findall(text)
    num_markers += len(mtchs)
print('{} markers in {} files'.format(num_markers, num_files))
