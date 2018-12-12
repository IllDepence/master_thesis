""" Compare sentence ends w/ citation marker to sentence ends w/o

    Conditional probability of citation given a certain pattern:
    P(CIT|PATT) = P(CIT) ∩ P(PATT) / P(PATT)
                  `-------v------´   `--v--´
                 citation_patt_prob general_patt_prob

    To play around with the required commonness of patterns:
        if general_patt_totals.get(patt[0], 0) < 10000:
    To get examples sentences use sentence_end_patterns.py
"""

import json
import operator
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

# # comb
# general_patt_fn = 'sentence_end_patts/sentence_comb.json'
# citation_patt_fn = 'sentence_end_patts/marker_comb.json'
# orig
general_patt_fn =  'sentence_end_patts/sentence_orig.json'
citation_patt_fn = 'sentence_end_patts/marker_orig.json'

# general patt probs
with open(general_patt_fn) as f:
    sentence_patts = json.load(f)
sentence_total = 0
for patt in sentence_patts:
    sentence_total += patt[1]
general_patt_probs = {}
general_patt_totals = {}
for patt in sentence_patts:
    general_patt_probs[patt[0]] = patt[1]/sentence_total
    general_patt_totals[patt[0]] = patt[1]

# citation patt probs
with open(citation_patt_fn) as f:
    marker_patts = json.load(f)
# marker_total = 0
# for patt in marker_patts:
#     marker_total += patt[1]
cond_patt_probs = {}
for patt in marker_patts:
    if '<EOS>¦' in patt[0]:
        continue
    if general_patt_totals.get(patt[0], 0) < 1000:
        continue
    # here it's okay to just go through marker_*_probs b/c patts not occuring
    # in it would lead to a conditional probability of 0 anyway
    citation_patt_prob = patt[1]/sentence_total
    general_patt_prob = general_patt_probs.get(patt[0], 0)
    cond_patt_probs[patt[0]] = citation_patt_prob / general_patt_prob


cond_patt_probs_sorted = sorted(cond_patt_probs.items(),
    key=operator.itemgetter(1), reverse=True
    )

for prob in cond_patt_probs_sorted[:50]:
    print(prob)
