""" Just playing around for the moment
"""

import os
import math
import sys
import random
from gensim import corpora, models, similarities


def recommend(docs_path):
    """ - foo
    """

    with open(docs_path) as f:
        lines = f.readlines()

    test = []
    train_aids = []
    train_texts = []
    tmp_bag = []
    tmp_bag_current_aid = lines[0].split(',')[0]
    texts = []  # for dictionary generation
    for line in lines:
        aid, text = line.split(',')
        text = text.replace('[]', '')
        texts.append(text.split())
        if aid != tmp_bag_current_aid:
            # tmp_bag now contains all lines sharing ID tmp_bag_current_aid
            num_contexts = len(tmp_bag)
            if num_contexts >= 4:
                # b/c some bibitems don't have a context we have to sort out
                # cases w/ too few contexts here
                num_train = math.floor(num_contexts * 0.8)
                num_test = num_contexts - num_train
                train_tuples = tmp_bag[:num_train]
                test_tuples = tmp_bag[-num_test:]
                test.extend(test_tuples)
                # because we use BOW we can just combine train docs here
                train_text_combined = ' '.join(tpl[1] for tpl in train_tuples)
                train_aids.append(tmp_bag_current_aid)
                train_texts.append(train_text_combined.split())
            # reset bag
            tmp_bag = []
            tmp_bag_current_aid = aid
        tmp_bag.append((aid, text))
    dictionary = corpora.Dictionary(texts)
    # dictionary.save('1712_test.dict')
    num_unique_tokens = len(dictionary.keys())
    # print(dictionary.token2id)
    corpus = [dictionary.doc2bow(text) for text in train_texts]
    # corpora.MmCorpus.serialize('1712_test_corpus.mm', corpus)
    # print(corpus)
    tfidf = models.TfidfModel(corpus)

    total = 0
    num_cur = 0
    num_top = 0
    num_top_5 = 0
    num_top_10 = 0
    print('test set size: {}\n- - - - - - - -'.format(len(test)))
    for tpl in test:
        test_aid = tpl[0]
        test_text = tpl[1].split()
        test_bow = dictionary.doc2bow(test_text)
        index = similarities.SparseMatrixSimilarity(
                    tfidf[corpus],
                    num_features=num_unique_tokens)
        sims = index[tfidf[test_bow]]
        sims_list = list(enumerate(sims))
        sims_list.sort(key=lambda tup: tup[1], reverse=True)
        # print('correct: {}'.format(test_aid))
        # print('- - - - - - - -')
        # for idx, sim in enumerate(sims_list[:11]):
        #     pre = '{} '.format(idx)
        #     if train_aids[sim[0]] == test_aid:
        #         pre += '✔ '
        #     else:
        #         pre += '  '
        #     print('{}{}: {}'.format(pre, sim[1], train_aids[sim[0]]))
        placement = len(sims_list)
        for idx, sim in enumerate(sims_list):
            if train_aids[sim[0]] == test_aid:
                placement = idx+1
                break
        if placement == 1:
            num_top += 1
        if placement <= 5:
            num_top_5 += 1
        if placement <= 10:
            num_top_10 += 1
        total += placement
        num_cur += 1
        print('- - - - - {}/{} - - - - -'.format(num_cur, len(test)))
        print('#1: {}'.format(num_top))
        print('in top 5: {}'.format(num_top_5))
        print('in top 10: {}'.format(num_top_10))
        print('avg: {}'.format(total/num_cur))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('usage: python3 recommend.py </path/to/docs_file>')
        sys.exit()
    docs_path = sys.argv[1]
    recommend(docs_path)
