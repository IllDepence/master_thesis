import re
import sys
from nltk import pos_tag

MAINCITS_PATT = re.compile(r'((CIT , )*MAINCIT( , CIT)*)')
CITS_PATT = re.compile(r'(((?<!MAIN)CIT , )*(?<!MAIN)CIT( , (?<!MAIN)CIT)*)')
QUOTE_PATT = re.compile(r'(\.|\?|!)("|\')?\s*\\x{241F}', re.I)
E_G_PATT = re.compile(r'(?<=\W)e\.\sg\.(?=\W)', re.I)

def merge_citation_token_lists(s):
    s = MAINCITS_PATT.sub('MAINCIT', s)
    s = CITS_PATT.sub('CIT', s)
    return s

with open('context_patts_all_2018.csv', 'w') as fo:
    with open('items_all_2018_lengthfix_1s.csv') as fi:
        for i, line in enumerate(fi):
            if i%100000 == 0:
                print('{}/29203189'.format(i))
            vals = line.strip().split('\u241E')
            cited_id = vals[0]
            cited_ids_adj = vals[1]
            citing_id = vals[2]
            marker = ' \u241F '
            sentence_orig = vals[3]
            sentence = merge_citation_token_lists(sentence_orig)
            sentence = re.sub('MAINCIT', marker, sentence_orig)
            sentence = re.sub(QUOTE_PATT, ' {}.'.format(marker), sentence)
            if marker not in sentence:
                print('Problem w/ line {}: "{}"'.format(i, line))
            words = pos_tag(sentence.split())
            words = [w for w in words if re.search(r'[\w|\u241F]', w[0])]
            sent_len = len(words)
            indices = [i for i, tup in enumerate(words)
                       if tup[0] == marker.strip()]
            for word_idx in indices:
                word = words[word_idx][0]
                if word == marker.strip():
                    patt_comb = [None, None, None, '[]', None, None, None]
                    patt_orig = [None, None, None, '[]', None, None, None]
                    for shift in range(-3, 4):
                        x_idx = shift+3
                        if shift == 0:
                            # marker itself
                            continue
                        if word_idx+shift < 0 or \
                                word_idx+shift >= len(words):
                            patt_comb[x_idx] = '<EOS>'
                            patt_orig[x_idx] = '<EOS>'
                            continue
                        wrd = words[word_idx+shift][0]
                        pos = words[word_idx+shift][1]
                        patt_orig[x_idx] = pos
                        if 'V' in pos:
                            patt_comb[x_idx] = 'V'
                        elif pos in ['NN', 'NNS']:
                            patt_comb[x_idx] = 'NN'
                        elif pos in ['NNP', 'NNPS']:
                            patt_comb[x_idx] = 'NNP'
                        elif pos == 'IN':
                            patt_comb[x_idx] = 'IN'
                        elif 'JJ' in pos:
                            patt_comb[x_idx] = 'JJ'
                        elif 'W' in pos:
                            patt_comb[x_idx] = 'WH'
                        elif 'RB' in pos:
                            patt_comb[x_idx] = 'ADV'
                        elif 'PR' in pos:
                            patt_comb[x_idx] = 'PR'
                        elif wrd == 'FORMULA':
                            patt_comb[x_idx] = 'FORMULA'
                        elif wrd == 'FIGURE':
                            patt_comb[x_idx] = 'FIGURE'
                        elif wrd == 'TABLE':
                            patt_comb[x_idx] = 'TABLE'
                        else:
                            patt_comb[x_idx] = 'OTHER'
                    comb_id = '¦'.join(patt_comb)
                    orig_id = '¦'.join(patt_orig)
            try:
                new_line = '\u241E'.join([cited_id, cited_ids_adj, citing_id, comb_id, orig_id])
                fo.write('{}\n'.format(new_line))
            except NameError:
                print(line)
                sys.exit()
