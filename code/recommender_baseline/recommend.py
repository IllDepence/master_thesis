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
    for idx, line in enumerate(lines):
        aid, adjacent, in_doc, text = line.split(',')
        # TODO: create adjacent map for later use in eval
        text = text.replace('[]', '')
        texts.append(text.split())
        if aid != tmp_bag_current_aid or idx == len(lines)-1:
            # tmp_bag now contains all lines sharing ID tmp_bag_current_aid
            num_contexts = len(tmp_bag)
            sub_bags_dict = {}
            for item in tmp_bag:
                item_in_doc = item[0]
                item_text = item[1]
                if item_in_doc not in sub_bags_dict:
                    sub_bags_dict[item_in_doc] = []
                sub_bags_dict[item_in_doc].append(item_text)
            order = sorted(sub_bags_dict,
                           key=lambda k: len(sub_bags_dict[k]),
                           reverse=True)
            # ↑ keys for sub_bags_dict, ordered for largest bag to smallest
            min_num_train = math.floor(num_contexts * 0.8)
            train_texts_comb = []
            test_texts = []
            # TODO: how to do k-fold cross val with this?
            for jdx, sub_bag_key in enumerate(order):
                sb_texts = sub_bags_dict[sub_bag_key]
                if len(train_texts_comb) > min_num_train or jdx == len(order)-1:
                    test_texts.extend(sb_texts)
                else:
                    train_texts_comb.extend(sb_texts)
            l_tr = len(train_texts_comb)
            l_te = len(test_texts)
            l_tr_perc = (l_tr/(l_tr+l_te))*100
            l_te_perc = (l_te/(l_tr+l_te))*100
            test.extend([(tmp_bag_current_aid, txt) for txt in test_texts])
            # because we use BOW we can just combine train docs here
            train_text_combined = ' '.join(txt for txt in train_texts_comb)
            train_aids.append(tmp_bag_current_aid)
            train_texts.append(train_text_combined.split())
            # reset bag
            tmp_bag = []
            tmp_bag_current_aid = aid
        tmp_bag.append([in_doc, text])
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
    ndcg_sum = 0
    map_sum = 0
    ndcg_sum_5 = 0
    map_sum_5 = 0
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
        ndcg_sum += 1 / math.log2(1 + placement)
        map_sum += 1 / placement
        if placement == 1:
            num_top += 1
        if placement <= 5:
            num_top_5 += 1
            ndcg_sum_5 += 1 / math.log2(1 + placement)
            map_sum_5 += 1 / placement
        if placement <= 10:
            num_top_10 += 1
        total += placement
        num_cur += 1
        print('- - - - - {}/{} - - - - -'.format(num_cur, len(test)))
        print('#1: {}'.format(num_top))
        print('in top 5: {}'.format(num_top_5))
        print('in top 10: {}'.format(num_top_10))
        print('avg: {}'.format(total/num_cur))
        print('ndcg: {}'.format(ndcg_sum/num_cur))
        print('map: {}'.format(map_sum/num_cur))
        print('ndcg@5: {}'.format(ndcg_sum_5/num_cur))
        print('map@5: {}'.format(map_sum_5/num_cur))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('usage: python3 recommend.py </path/to/docs_file>')
        sys.exit()
    docs_path = sys.argv[1]
    recommend(docs_path)
