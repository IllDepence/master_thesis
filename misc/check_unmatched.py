import os
import operator
import json
import requests
import time
from lxml import etree

ns = {'arxiv':'http://arxiv.org/schemas/atom'}

parser = etree.XMLParser()

if not os.path.isdir('single'):
    os.makedirs('single')

with open('181107_unmached.json') as f:
    um_map = json.load(f)

per_doc = {}
per_cit = {}
num_all = len(um_map)
idx = 0
per_cat = {}
for aid, num in um_map.items():
    idx += 1
    print('{}/{}'.format(idx, num_all))
    url = 'http://export.arxiv.org/api/query?search_query=id:{}'.format(aid)
    resp = requests.get(url)
    tree = etree.fromstring(resp.content, parser)
    pcat = None
    for cat in tree.xpath('//arxiv:primary_category', namespaces=ns):
        pcat = cat.get('term')
    if '.' in pcat:
        pcat = pcat.split('.')[0]
    if pcat not in per_doc:
        per_doc[pcat] = 0
    per_doc[pcat] += 1
    if pcat not in per_cit:
        per_cit[pcat] = 0
    per_cit[pcat] += num
    if pcat not in per_cat:
        per_cat[pcat] = []
    per_cat[pcat].append(aid)
    time.sleep(.1)

sorted_per_doc = sorted(per_doc.items(), key=operator.itemgetter(1),
                        reverse=True)
sorted_per_cit = sorted(per_cit.items(), key=operator.itemgetter(1),
                        reverse=True)

with open('per_cat', 'w') as f:
    f.write(json.dumps(per_cat))
with open('per_doc', 'w') as f:
    f.write('\n'.join(['{}: {}'.format(tup[0], tup[1])
                       for tup in sorted_per_doc]))

with open('per_cit', 'w') as f:
    f.write('\n'.join(['{}: {}'.format(tup[0], tup[1])
                       for tup in sorted_per_cit]))
