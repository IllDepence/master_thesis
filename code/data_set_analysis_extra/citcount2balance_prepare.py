""" Prepare citation count to citation distribution data
"""

import json
import operator

with open('citation_link_differences.json') as f:
  citmap = json.load(f)
counttups = []
for key, lists in citmap.items():
  counttups.append([len(lists[0]), len(lists[1]), len(lists[2])])
citcount_to_citbalance []
citcount_to_citbalance = []
for ct in counttups:
  citcount = sum(ct)
  citbalance = ct[0] - ct[2]
  citcount_to_citbalance.append([citcount, citbalance])
citcount_to_citbalance.sort(key = operator.itemgetter(0))
with open('citcount_to_citbalance', 'w') as fo:
  fo.write(json.dumps(citcount_to_citbalance))
