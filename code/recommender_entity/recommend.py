""" Recommend, using entities.
"""

import os
import math
import sys
import random
from gensim import corpora, models, similarities
from gensim.parsing.preprocessing import (preprocess_documents,
                                          preprocess_string,
                                          strip_multiple_whitespaces,
                                          strip_punctuation)


def recommend(docs_path):
    """ - foo
    """

    with open(docs_path) as f:
        lines = f.readlines()

    test = []
    train_aids = []
    train_texts = []
    tmp_bag = []
    tmp_bag_current_aid = lines[0].split('\u241E')[0]
    texts = []  # for dictionary generation
    adjacent_cit_map = {}
    for idx, line in enumerate(lines):
        # TODO
        # - make features out of entities
        # - make special features in case of <NE>[]
        # - mby also POS tagging then <preposition>[] special treatment
        #   etc.
        aid, adjacent, in_doc, text, annot_str = line.split('\u241E')
        # create adjacent map for later use in eval
        if aid not in adjacent_cit_map:
            adjacent_cit_map[aid] = []
        if len(adjacent) > 0:
            adj_cits = adjacent.split('\u241F')
            for adj_cit in adj_cits:
                if adj_cit not in adjacent_cit_map[aid]:
                    adjacent_cit_map[aid].append(adj_cit)
        if len(annot_str) > 0:
            annots = annot_str.split('\u241F')
        else:
            annots = []
        # fill texts
        custom_filter = [strip_punctuation,
                         strip_multiple_whitespaces]
        words = preprocess_string(text, custom_filter)
        tokens = words + annots
        texts.append(tokens)
        text = ' '.join(tokens)
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
    # average number of adjacent docs
    # adj_sum = 0
    # for k, v in adjacent_cit_map.items():
    #     adj_sum += len(v)
    # print(adj_sum/len(adjacent_cit_map))
    dictionary = corpora.Dictionary(texts)
    # dictionary.save('1712_test.dict')
    num_unique_tokens = len(dictionary.keys())
    # print(dictionary.token2id)
    corpus = [dictionary.doc2bow(text) for text in train_texts]
    # corpora.MmCorpus.serialize('1712_test_corpus.mm', corpus)
    # print(corpus)
    tfidf = models.TfidfModel(corpus)

    num_cur = 0
    num_top = 0
    num_top_5 = 0
    num_top_10 = 0
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
        rank = len(sims_list)
        for idx, sim in enumerate(sims_list):
            if train_aids[sim[0]] == test_aid:
                rank = idx+1
                break
            if idx >= 10:
                break
        dcg = 0
        idcg = 0
        num_rel = 1 + len(adjacent_cit_map[test_aid])
        for i in range(5):
            placement = i+1
            sim = sims_list[i]
            result_aid = train_aids[sim[0]]
            if result_aid == test_aid:
                relevance = 1
            elif result_aid in adjacent_cit_map[test_aid]:
                relevance = .5
            else:
                relevance = 0
            denom = math.log2(placement + 1)
            dcg_numer = math.pow(2, relevance) - 1
            dcg += dcg_numer / denom
            if placement == 1:
                ideal_rel = 1
            elif placement <= num_rel:
                ideal_rel = .5
            else:
                ideal_rel = 0
            idcg_numer = math.pow(2, ideal_rel) - 1
            idcg += idcg_numer / denom
        ndcg = dcg / idcg
        if rank == 1:
            num_top += 1
        if rank <= 5:
            num_top_5 += 1
            map_sum_5 += 1 / rank
            ndcg_sum_5 += ndcg
        if rank <= 10:
            num_top_10 += 1
        num_cur += 1
        print('- - - - - {}/{} - - - - -'.format(num_cur, len(test)))
        print('#1: {}'.format(num_top))
        print('in top 5: {}'.format(num_top_5))
        print('in top 10: {}'.format(num_top_10))
        print('ndcg@5: {}'.format(ndcg_sum_5/num_cur))
        print('map@5: {}'.format(map_sum_5/num_cur))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('usage: python3 recommend.py </path/to/docs_file>')
        sys.exit()
    docs_path = sys.argv[1]
    recommend(docs_path)
