""" Compare sentence ends w/ citation marker to sentence ends w/o

    Conditional probability of citation given a certain pattern:
    P(CIT|PATT) = P(CIT) ∩ P(PATT) / P(PATT)
                  `-------v------´   `--v--´
                 citation_patt_prob general_patt_prob


    # TODO:
        - filter too short sentences in JSON generation
        - work in example sentences
        - work in number of sentences
"""

import json
import operator
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

# general patt probs
with open('sentence_end_patts/sentence_comb.json') as f:
    sentence_comb_patts = json.load(f)
sentence_comb_total = 0
for patt in sentence_comb_patts:
    sentence_comb_total += patt[1]
general_patt_probs = {}
general_patt_totals = {}
for patt in sentence_comb_patts:
    general_patt_probs[patt[0]] = patt[1]/sentence_comb_total
    general_patt_totals[patt[0]] = patt[1]

# citation patt probs
with open('sentence_end_patts/marker_comb.json') as f:
    marker_comb_patts = json.load(f)
# marker_comb_total = 0
# for patt in marker_comb_patts:
#     marker_comb_total += patt[1]
cond_patt_probs = {}
for patt in marker_comb_patts:
    if '<EOS>¦' in patt[0]:
        continue
    # here it's okay to just go through marker_*_probs b/c patts not occuring
    # in it would lead to a conditional probability of 0 anyway
    citation_patt_prob = patt[1]/sentence_comb_total
    general_patt_prob = general_patt_probs.get(patt[0], 0)
    cond_patt_probs[patt[0]] = citation_patt_prob / general_patt_prob


cond_patt_probs_sorted = sorted(cond_patt_probs.items(),
    key=operator.itemgetter(1), reverse=True
    )

for prob in cond_patt_probs_sorted[:325]:
    print(prob)


import sys
sys.exit()

with open('sentence_end_patts/sentence_oirg.json') as f:
    sentence_oirg_patts = json.load(f)
sentence_oirg_total = len(sentence_oirg_patts)
with open('sentence_end_patts/marker_oirg.json') as f:
    marker_oirg_patts = json.load(f)
marker_orig_total = len(marker_orig_patts)
