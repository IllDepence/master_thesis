""" Positions of citation markers in sentences, relatve to where in doc
"""

import json
import math
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


def sent_pos(in_dir):
    """ Positions of citation markers in sentences, relatve to where in doc
    """

    arxiv_base_url = 'http://export.arxiv.org/api/query?search_query=id:'
    arxiv_ns = {'atom': 'http://www.w3.org/2005/Atom',
                'opensearch': 'http://a9.com/-/spec/opensearch/1.1/',
                'arxiv': 'http://arxiv.org/schemas/atom'}

    punkt_param = PunktParameters()
    abbreviation = ['al', 'fig', 'e.g', 'i.e', 'eq', 'cf']
    punkt_param.abbrev_types = set(abbreviation)
    tokenizer = PunktSentenceTokenizer(punkt_param)

    with open('hedge_words') as f:
        hedge_words = [l.strip() for l in f.readlines()]

    x_all = list(range(-5, 6))
    y_verb = []
    y_noun = []
    y_propnoun = []
    y_prepos = []
    y_adj = []
    y_wh = []
    y_adv = []
    y_pr = []
    y_form = []
    y_fig = []
    y_tab = []
    for x in x_all:
        y_verb.append(0)
        y_noun.append(0)
        y_propnoun.append(0)
        y_prepos.append(0)
        y_adj.append(0)
        y_wh.append(0)
        y_adv.append(0)
        y_pr.append(0)
        y_form.append(0)
        y_fig.append(0)
        y_tab.append(0)
    file_names = os.listdir(in_dir)
    for file_idx, fn in enumerate(file_names):
        if file_idx%100 == 0:
            print('{}/{}'.format(file_idx, len(file_names)))
        path = os.path.join(in_dir, fn)
        aid, ext = os.path.splitext(fn)
        if ext != '.txt' or aid == 'log':
            continue

        phys_cat = ['hep-th','hep-ph','hep-lat','hep-ex','cond-mat','astro-ph',
                    'physics','nucl','gr-qc','quant-ph','nlin']
        math_cat = ['math','math-ph']
        cs_cat = ['cs']
        if re.search(r'[a-z]', aid):
            split = re.search(r'[a-z][0-9]', aid).span()[0] + 1
            aid = aid[:split] + '/' + aid[split:]
        resp = requests.get(
            '{}{}&start=0&max_results=1'.format(arxiv_base_url, aid))
        xml_root = etree.fromstring(resp.text.encode('utf-8'))
        result_elems = xml_root.xpath('/atom:feed/atom:entry',
                                      namespaces=arxiv_ns)
        result = result_elems[0]
        cat = result.find('arxiv:primary_category', namespaces=arxiv_ns).get('term')
        high_cat = None
        for pc in phys_cat:
            if pc in cat:
                high_cat = 'phys'
                break
        if not high_cat:
            for mc in math_cat:
                if pc in cat:
                    high_cat = 'math'
                    break
        if not high_cat:
            if 'cs' in cat:
                high_cat = 'cs'
        if not high_cat:
            continue

        if high_cat != 'phys':
            continue

        with open(path) as f:
            text = f.read()

        marker = ' \u241F '
        doc_len = len(text)
        for sent_idx, sent_edx in tokenizer.span_tokenize(text):
            sentence_orig = text[sent_idx:sent_edx]
            sentence = re.sub(CITE_MULTI_PATT, marker, sentence_orig)
            sentence = re.sub(QUOTE_PATT, ' {}.'.format(marker), sentence)
            if marker in sentence:
                words = pos_tag(sentence.split())
                words = [w for w in words if re.search(r'[\w|\u241F]', w[0])]
                sent_len = len(words)
                indices = [i for i, tup in enumerate(words)
                           if tup[0] == marker.strip()]
                for word_idx in indices:
                    word = words[word_idx][0]
                    if word == marker.strip():
                        for shift in x_all:
                            x_idx = shift+5
                            if shift == 0:
                                # marker itself
                                continue
                            if word_idx+shift < 0 or \
                                    word_idx+shift >= len(words):
                                # out of range
                                continue
                            wrd = words[word_idx+shift][0]
                            pos = words[word_idx+shift][1]
                            if 'V' in pos:
                                y_verb[x_idx] += 1
                            if pos in ['NN', 'NNS']:
                                y_noun[x_idx] += 1
                            if pos in ['NNP', 'NNPS']:
                                y_propnoun[x_idx] += 1
                            if pos == 'IN':
                                y_prepos[x_idx] += 1
                            if 'JJ' in pos:
                                y_adj[x_idx] += 1
                            if 'W' in pos:
                                y_wh[x_idx] += 1
                            if 'RB' in pos:
                                y_adv[x_idx] += 1
                            if 'PR' in pos:
                                y_pr[x_idx] += 1
                            if wrd == 'FORMULA':
                                y_form[x_idx] += 1
                            if wrd == 'FIGURE':
                                y_fig[x_idx] += 1
                            if wrd == 'TABLE':
                                y_tab[x_idx] += 1
        if file_idx > 200:
           break

    for idx, y in enumerate([(y_verb, 'verb'),
                             (y_noun, 'noun'),
                             (y_propnoun, 'proper noun'),
                             (y_prepos, 'preposition'),
                             (y_adj, 'adjective'),
                             (y_wh, 'wh-det./-adv./-pron.'),
                             (y_adv, 'adverb'),
                             (y_pr, 'pers./pos. pronoun'),
                             (y_form, 'formula')
                            ]):
        color = list(mpl.rcParams['axes.prop_cycle'])[idx]['color']
        plt.plot(x_all, y[0], marker='', linestyle='-', linewidth=.5, alpha=0.3, color=color)
        plt.plot(x_all, y[0], label=y[1], marker='D', linestyle='', color=color)

    plt.xlabel('word position relative to citation')
    plt.ylabel('number of words')
    plt.legend()

    ax = plt.gca()
    ax.xaxis.grid(True)
    plt.xticks(np.arange(min(x_all), max(x_all), 1.0))

    plt.show()

if __name__ == '__main__':
    if len(sys.argv) not in [2, 3]:
        print('usage: python3 generate_dataset.py </path/to/in/dir>')
        sys.exit()
    in_dir = sys.argv[1]
    ret = sent_pos(in_dir)
    if not ret:
        sys.exit()
