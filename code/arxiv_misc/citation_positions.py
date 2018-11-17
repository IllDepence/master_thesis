""" Positions of citation markers in sentences, relatve to where in doc
"""

import json
import math
import os
import re
import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from nltk import pos_tag
from nltk.tokenize.punkt import PunktSentenceTokenizer, PunktParameters

CITE_MULTI_PATT = re.compile(r'(\{\{cite:[0-9A-F-]+\}\}(, )?)+', re.I)
QUOTE_PATT = re.compile(r'(\.|\?|!)("|\')?\s*\\x{241F}', re.I)


def sent_pos(in_dir):
    """ Positions of citation markers in sentences, relatve to where in doc
    """

    punkt_param = PunktParameters()
    abbreviation = ['al', 'fig', 'e.g', 'i.e', 'eq', 'cf']
    punkt_param.abbrev_types = set(abbreviation)
    tokenizer = PunktSentenceTokenizer(punkt_param)

    x = []
    y = []
    file_names = os.listdir(in_dir)
    buckets = []
    for foo in range(10):
        buckets.append([0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    for file_idx, fn in enumerate(file_names):
        if file_idx%100 == 0:
            print('{}/{}'.format(file_idx, len(file_names)))
        path = os.path.join(in_dir, fn)
        aid, ext = os.path.splitext(fn)
        if ext != '.txt' or aid == 'log':
            continue
        with open(path) as f:
            text = f.read()

        marker = ' \u241F '
        text = re.sub(CITE_MULTI_PATT, marker, text)
        text = re.sub(QUOTE_PATT, ' {}.'.format(marker), text)

        sentences = tokenizer.tokenize(text)
        doc_len = len(sentences)
        for sent_idx, sentence in enumerate(sentences):
            if marker in sentence:
                doc_pos = 1 - (sent_idx/doc_len)
                buck_y_idx = math.floor(doc_pos*10)
                if buck_y_idx == 10:
                    buck_y_idx = 9
                words = pos_tag(sentence.split())
                words = [w for w in words if re.search(r'[\w|\u241F]', w[0])]
                sent_len = len(words)
                indices = [i for i, tup in enumerate(words)
                           if tup[0] == marker.strip()]
                for word_idx in indices:
                    word = words[word_idx][0]
                    # if word == marker.strip():
                    # if word == marker.strip() and \
                    #     words[word_idx-1][1] == 'IN':
                    # if word == marker.strip() and \
                    #     ((word_idx > 0 and \
                    #       'FORMULA' not in words[word_idx-1][0] and \
                    #       words[word_idx-1][1] in ['NNP', 'NNPS']) or \
                    #      (word_idx > 1 and \
                    #       words[word_idx-1][1] in ['NN', 'NNS'] and \
                    #       'FORMULA' not in words[word_idx-2][0] and \
                    #       words[word_idx-2][1] in ['NNP', 'NNPS'])):
                    if word == marker.strip() and \
                        word_idx+1 < len(words) and \
                        'VB' in words[word_idx+1][1]:
                        # print(words)
                        # print('doc pos:  {}'.format((sent_idx/doc_len)))
                        # print('sent pos: {}/{}'.format((word_idx+1),sent_len))
                        # input()
                        sent_pos = (word_idx+1)/sent_len
                        y.append(doc_pos)
                        x.append(sent_pos)
                        buck_x_idx = math.floor(sent_pos* 10)
                        if buck_x_idx == 10:
                            buck_x_idx = 9
                        buckets[buck_y_idx][buck_x_idx] += 1
        # ↓ character wise
        # for sent_idx, sentence in enumerate(sentences):
        #     sent_len = len(sentence)
        #     doc_pos = 1 - (sent_idx/doc_len)
        #     buck_y_idx = math.floor(doc_pos*10)
        #     if buck_y_idx == 10:
        #         buck_y_idx = 9
        #     for cit_mark in re.finditer(marker, sentence):
        #         cm_idx = cit_mark.end()
        #         sent_pos = cm_idx/sent_len
        #         y.append(doc_pos)
        #         x.append(sent_pos)
        #         buck_x_idx = math.floor(sent_pos*10)
        #         if buck_x_idx == 10:
        #             buck_x_idx = 9
        #         buckets[buck_y_idx][buck_x_idx] += 1

    print('normalized row distributions:')
    for line in buckets:
        print(' '.join(['{:.2f}'.format(x/sum(line)) for x in line]))

    plt.xlabel('citation marker position in sentence')
    plt.ylabel('sentence position in document')

    heatmap, xedges, yedges = np.histogram2d(x, y, bins=(50))
    extent = [xedges[0], xedges[-1], yedges[0], yedges[-1]]
    # plt.imshow(heatmap.T, extent=extent, origin='lower', norm=LogNorm())
    plt.imshow(heatmap.T, extent=extent, origin='lower')
    plt.colorbar()
    plt.show()

if __name__ == '__main__':
    if len(sys.argv) not in [2, 3]:
        print('usage: python3 generate_dataset.py </path/to/in/dir>')
        sys.exit()
    in_dir = sys.argv[1]
    ret = sent_pos(in_dir)
    if not ret:
        sys.exit()
