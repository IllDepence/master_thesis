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
E_G_PATT = re.compile(r'(?<=\W)e\.\sg\.(?=\W)', re.I)


def sent_pos(in_dir):
    """ Positions of citation markers in sentences, relatve to where in doc
    """

    punkt_param = PunktParameters()
    abbreviation = ['al', 'fig', 'e.g', 'i.e', 'eq', 'cf', 'ref', 'refs']
    punkt_param.abbrev_types = set(abbreviation)
    tokenizer = PunktSentenceTokenizer(punkt_param)

    with open('hedge_words') as f:
        hedge_words = [l.strip() for l in f.readlines()]

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
        text = re.sub(E_G_PATT, 'e.g.', text)
        # annot_fn = '{}_annot.json'.format(aid)
        # annot_path = os.path.join(in_dir, annot_fn)
        # if not os.path.isfile(annot_path):
        #     continue
        # with open(annot_path) as f:
        #     annots = json.load(f)

        marker = ' \u241F '
        doc_len = len(text)
        # ↓ word wise
        for sent_idx, sent_edx in tokenizer.span_tokenize(text):
            sentence_orig = text[sent_idx:sent_edx]
            sentence = re.sub(CITE_MULTI_PATT, marker, sentence_orig)
            sentence = re.sub(QUOTE_PATT, ' {}.'.format(marker), sentence)
            # determine contained annotations
            # annotated_words = []
            # for annot in annots:
            #     start = annot[0]
            #     end = annot[1]
            #     dbp_id = annot[2]
            #     annot_len = end - start
            #     in_sent_idx = start - sent_idx
            #     if start >= sent_idx and end <= sent_edx:
            #         disp = sentence_orig[in_sent_idx:in_sent_idx+annot_len]
            #         annotated_words.append(disp)
            if marker in sentence:
                doc_pos = 1 - (sent_idx/doc_len)
                buck_y_idx = math.floor(doc_pos*10)
                if buck_y_idx == 10:
                    buck_y_idx = 9
                words = pos_tag(sentence.split())
                words = [w for w in words if re.search(r'[\w|\u241F]', w[0])]
                sent_len = len(words)
                sent_tags_str = ' '.join([tup[1] for tup in words])
                indices = [i for i, tup in enumerate(words)
                           if tup[0] == marker.strip()]
                # if 'JJS' not in sent_tags_str:
                #     continue
                for word_idx in indices:
                    word = words[word_idx][0]
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

                    # if word == marker.strip() and \
                    #     (word_idx > 0 and \
                    #      words[word_idx-1][0] in annotated_words and \
                    #      words[word_idx-1][1] in ['NNP', 'NNPS']):

                    # if word == marker.strip() and \
                    #     word_idx+1 < len(words) and \
                    #     'VB' in words[word_idx+1][1]:

                    if word == marker.strip():
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
        # if file_idx > 1000:
        #     break

        # # ↓ character wise
        # for sent_idx, sentence in enumerate(sentences):
        #     # has_hw = False
        #     # for hw in hedge_words:
        #     #     if hw in sentence:
        #     #         has_hw = True
        #     #         break
        #     # if not has_hw:
        #     #     continue
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
    plt.imshow(heatmap.T, extent=extent, origin='lower', norm=LogNorm())
    # plt.imshow(heatmap.T, extent=extent, origin='lower')
    plt.colorbar()
    plt.show()

    plt.clf()

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
