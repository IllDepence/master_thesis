""" Convert https://docs.google.com/spreadsheets/d/1SVnofZmuAwYIuZQv-usmEdj5bu_
            B5z3-hMtfs4gcre4/edit?usp=sharing
    to recommender friendly format.
"""

import operator
import os
import re
import sys

CIT_PATT = re.compile(r'<(GC|DBLP):([^>]+)>')

fns = os.listdir('.')
out_file = 'items_acl-arc.csv'
contexts = []

for file_idx, fn in enumerate(fns):
    if file_idx%100 == 0:
        print('{}/{}'.format(file_idx, len(fns)))
    citing_id, ext = os.path.splitext(fn)
    if ext != '.txt':
        continue
    with open(fn) as f:
        for line in f:
            # if it contains at least one citation
            if CIT_PATT.search(line):
                # go through all citations
                for m in CIT_PATT.finditer(line):
                    # get ID of cited doc
                    cited_id = m.group(2)
                    # replace inline citation markers
                    text = m.string.replace(m.group(0), 'MAINCIT').strip()
                    text = CIT_PATT.sub('CIT', text)
                    adjacent = ''
                    contexts.append([cited_id, adjacent, citing_id, text])

contexts.sort(key=operator.itemgetter(0))

with open(out_file, 'w') as f:
    for context_vals in contexts:
        f.write('{}\n'.format('\u241E'.join(context_vals)))

# # only DBLP resolved citations
# CIT_PATT_DBLP = re.compile(r'<DBLP:([^>]+)>')
# CIT_PATT = re.compile(r'<(GC|DBLP):([^>]+)>')
# 
# fns = os.listdir('.')
# out_file = 'items_acl-arc_DBLPonly.csv'
# contexts = []
# 
# for file_idx, fn in enumerate(fns):
#     if file_idx%100 == 0:
#         print('{}/{}'.format(file_idx, len(fns)))
#     citing_id, ext = os.path.splitext(fn)
#     if ext != '.txt':
#         continue
#     with open(fn) as f:
#         for line in f:
#             # if it contains at least one citation
#             if CIT_PATT_DBLP.search(line):
#                 # go through all citations
#                 for m in CIT_PATT_DBLP.finditer(line):
#                     # get ID of cited doc
#                     cited_id = m.group(1)
#                     # replace inline citation markers
#                     text = m.string.replace(m.group(0), 'MAINCIT').strip()
#                     text = CIT_PATT.sub('CIT', text)
#                     adjacent = ''
#                     contexts.append([cited_id, adjacent, citing_id, text])
