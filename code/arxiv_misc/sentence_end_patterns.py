""" Generate JSON files with the most common PoS tag triplets at the end of a
    sentence, for sentences in general and separately for sentences ending in
    a citation.
"""

import json
import math
import operator
import os
import re
import requests
import sys
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from lxml import etree
from matplotlib.colors import LogNorm
from nltk import pos_tag
from nltk.tokenize.punkt import PunktSentenceTokenizer, PunktParameters

CITE_MULTI_PATT = re.compile(r'(\{\{cite:[0-9A-F-]+\}\}(, )?)+', re.I)
QUOTE_PATT = re.compile(r'(\.|\?|!)("|\')?\s*\\x{241F}', re.I)
E_G_PATT = re.compile(r'(?<=\W)e\.\sg\.(?=\W)', re.I)


def marker_surr_patt(in_dir):
    """ Find most frequent POS tag patterns at the end of sentences.
    """

    punkt_param = PunktParameters()
    abbreviation = ['al', 'fig', 'e.g', 'i.e', 'eq', 'cf', 'ref', 'refs']
    punkt_param.abbrev_types = set(abbreviation)
    tokenizer = PunktSentenceTokenizer(punkt_param)

    file_names = os.listdir(in_dir)
    patt_comb_freq_map = {}
    patt_orig_freq_map = {}
    patt_comb_freq_map_cit = {}
    patt_orig_freq_map_cit = {}
    # num_sentences_total = 0
    for file_idx, fn in enumerate(file_names):
        if file_idx%100 == 0:
            print('{}/{}'.format(file_idx, len(file_names)))
            # print(num_sentences_total/(file_idx+1))
        path = os.path.join(in_dir, fn)
        aid, ext = os.path.splitext(fn)
        if ext != '.txt' or aid == 'log':
            continue

        if re.search(r'[a-z]', aid):
            split = re.search(r'[a-z][0-9]', aid).span()[0] + 1
            aid = aid[:split] + '/' + aid[split:]

        with open(path) as f:
            text = f.read()
        text = re.sub(E_G_PATT, 'e.g.', text)

        if not re.search(CITE_MULTI_PATT, text):
            continue

        marker = ' \u241F '
        doc_len = len(text)
        for sent_idx, sent_edx in tokenizer.span_tokenize(text):
            cit_end = False
            sentence_orig = text[sent_idx:sent_edx]
            sentence = re.sub(CITE_MULTI_PATT, marker, sentence_orig)
            sentence = re.sub(QUOTE_PATT, ' {}.'.format(marker), sentence)
            words = pos_tag(sentence.split())
            words = [w for w in words if re.search(r'[\w|\u241F]', w[0])]
            if len(words) == 0:
                continue
            if words[-1][0] == marker.strip():
                cit_end = True
                words = words[:-1]
            if len(words) < 3:
                continue
            # num_sentences_total += 1
            sent_len = len(words)
            patt_comb = [None, None, None, None]
            patt_orig = [None, None, None, None]
            for x_idx in range(sent_len-3, sent_len+1):
                patt_idx = x_idx - (sent_len-3)
                if x_idx < 0 or \
                        x_idx >= len(words):
                    patt_comb[patt_idx] = '<EOS>'
                    patt_orig[patt_idx] = '<EOS>'
                    continue
                wrd = words[x_idx][0]
                pos = words[x_idx][1]
                patt_orig[patt_idx] = pos
                if 'V' in pos:
                    patt_comb[patt_idx] = 'V'
                elif pos in ['NN', 'NNS']:
                    patt_comb[patt_idx] = 'NN'
                elif pos in ['NNP', 'NNPS']:
                    patt_comb[patt_idx] = 'NNP'
                elif pos == 'IN':
                    patt_comb[patt_idx] = 'IN'
                elif 'JJ' in pos:
                    patt_comb[patt_idx] = 'JJ'
                elif 'W' in pos:
                    patt_comb[patt_idx] = 'WH'
                elif 'RB' in pos:
                    patt_comb[patt_idx] = 'ADV'
                elif 'PR' in pos:
                    patt_comb[patt_idx] = 'PR'
                elif wrd == 'FORMULA':
                    patt_comb[patt_idx] = 'FORMULA'
                elif wrd == 'FIGURE':
                    patt_comb[patt_idx] = 'FIGURE'
                elif wrd == 'TABLE':
                    patt_comb[patt_idx] = 'TABLE'
                else:
                    patt_comb[patt_idx] = 'OTHER'
            comb_id = '¦'.join(patt_comb)
            orig_id = '¦'.join(patt_orig)
            if comb_id not in patt_comb_freq_map:
                patt_comb_freq_map[comb_id] = 0
            patt_comb_freq_map[comb_id] += 1
            if cit_end:
                if comb_id not in patt_comb_freq_map_cit:
                    patt_comb_freq_map_cit[comb_id] = 0
                patt_comb_freq_map_cit[comb_id] += 1

            if orig_id not in patt_orig_freq_map:
                patt_orig_freq_map[orig_id] = 0
            patt_orig_freq_map[orig_id] += 1
            if cit_end:
                if orig_id not in patt_orig_freq_map_cit:
                    patt_orig_freq_map_cit[orig_id] = 0
                patt_orig_freq_map_cit[orig_id] += 1
                if orig_id == 'RB¦JJ¦NNS¦<EOS>':
                    print(sentence)
                    print(fn)
                    input()
        # if file_idx > 200:
        #    break

    patt_comb_freq = sorted(patt_comb_freq_map.items(),
                            key=operator.itemgetter(1), reverse=True)
    patt_orig_freq = sorted(patt_orig_freq_map.items(),
                            key=operator.itemgetter(1), reverse=True)
    patt_comb_freq_cit = sorted(patt_comb_freq_map_cit.items(),
                            key=operator.itemgetter(1), reverse=True)
    patt_orig_freq_cit = sorted(patt_orig_freq_map_cit.items(),
                            key=operator.itemgetter(1), reverse=True)
    print('- - - C O M B - - -')
    for pid in patt_comb_freq[:25]:
        print(pid)
    print('- - - O R I G - - -')
    for pid in patt_orig_freq[:25]:
        print(pid)

    with open('sentence_comb.json', 'w') as f:
        json.dump(patt_comb_freq, f)
    with open('sentence_orig.json', 'w') as f:
        json.dump(patt_orig_freq, f)
    with open('marker_comb.json', 'w') as f:
        json.dump(patt_comb_freq_cit, f)
    with open('marker_orig.json', 'w') as f:
        json.dump(patt_orig_freq_cit, f)

if __name__ == '__main__':
    if len(sys.argv) not in [2, 3]:
        print('usage: python3 generate_dataset.py </path/to/in/dir>')
        sys.exit()
    in_dir = sys.argv[1]
    ret = marker_surr_patt(in_dir)
    if not ret:
        sys.exit()
