""" Just playing around for the moment
"""

import os
import sys
import random
from gensim import corpora, models, similarities


def recommend(docs_path):
    """ - pick one random doc
        - calculate most similar docs based on TFIDF
        - list 10 most similar and indicate if they're for the same cited doc
    """

    with open(docs_path) as f:
        lines = f.readlines()

    texts = []
    aids = []
    test_idx = random.randint(0, len(lines))
    test_text = ''
    test_aid = ''
    aid_idx_map = {}
    for idx, line in enumerate(lines):
        if idx == test_idx:
            test_aid, test_text = line.split(',')
            test_text.replace('[]', '')
            test_text = test_text.split()
            continue
        aid, text = line.split(',')
        text = text.replace('[]', '')
        texts.append(text.split())
        aids.append(aid)
        if aid not in aid_idx_map:
            aid_idx_map[aid] = []
        aid_idx_map[aid].append(idx)
    dictionary = corpora.Dictionary(texts)
    # dictionary.save('1712_test.dict')
    # print(dictionary) <-- number of tokens given here has to be used below
    #                       as num_features
    # print(dictionary.token2id)
    corpus = [dictionary.doc2bow(text) for text in texts]
    # corpora.MmCorpus.serialize('1712_test_corpus.mm', corpus)
    # print(corpus)
    tfidf = models.TfidfModel(corpus)
    test_bow = dictionary.doc2bow(test_text)
    index = similarities.SparseMatrixSimilarity(tfidf[corpus],
                                                num_features=15233)
    sims = index[tfidf[test_bow]]
    sims_list = list(enumerate(sims))
    sims_list.sort(key=lambda tup: tup[1], reverse=True)
    print('similar to: {} ({})'.format(test_aid, test_idx))
    print('correct: {}'.format(aid_idx_map[test_aid]))
    print('- - - - - - - -')
    for sim in sims_list[:11]:
        if aids[sim[0]] == test_aid:
            pre = '✔ '
        else:
            pre = '  '
        print('{}{}: {}'.format(pre, sim[1], sim[0]))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('usage: python3 recommend.py </path/to/docs_file>')
        sys.exit()
    docs_path = sys.argv[1]
    recommend(docs_path)
