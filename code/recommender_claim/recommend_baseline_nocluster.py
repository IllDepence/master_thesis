""" Recommend using TFIDF/BOW approach.
"""

import os
import math
import sys
import random
import operator
from gensim import corpora, models, similarities
from util import bow_preprocess_string
from sklearn.preprocessing import MultiLabelBinarizer


def combine_rankings(bow_ranking, fos_ranking):
    point_dic = {}
    for i in range(len(bow_ranking)):
        points = len(bow_ranking) - i
        if bow_ranking[i] not in point_dic:
            point_dic[bow_ranking[i]] = 0
        point_dic[bow_ranking[i]] += points
        # FIXME: find a way to actually make use of FoS ranking
        if i < 5 and bow_ranking[i] == fos_ranking[0]:
            point_dic[bow_ranking[i]] *= 1.1
    comb = sorted(point_dic.items(), key=operator.itemgetter(1), reverse=True)
    return [c[0] for c in comb]

def recommend(docs_path, dict_path, fos_annot=True):
    """ - foo
    """

    test = []
    train_mids = []
    train_texts = []
    train_foss = []
    foss = []
    tmp_bag = []
    adjacent_cit_map = {}

    print('checking file length')
    num_lines = sum(1 for line in open(docs_path))

    print('train/test splitting')
    with open(docs_path) as f:
        for idx, line in enumerate(f):
            if idx == 0:
                tmp_bag_current_mid = line.split('\u241E')[0]
            if idx%10000 == 0:
                print('{}/{} lines'.format(idx, num_lines))
            cntxt_foss = []
            if fos_annot:
                mid, adjacent, in_doc, text, fos_annot = line.split('\u241E')
                cntxt_foss = [f.strip() for f in fos_annot.split('\u241F')]
                foss.extend(cntxt_foss)
            else:
                mid, adjacent, in_doc, text = line.split('\u241E')
            # create adjacent map for later use in eval
            if mid not in adjacent_cit_map:
                adjacent_cit_map[mid] = []
            if len(adjacent) > 0:
                adj_cits = adjacent.split('\u241F')
                for adj_cit in adj_cits:
                    if adj_cit not in adjacent_cit_map[mid]:
                        adjacent_cit_map[mid].append(adj_cit)
            # fill texts
            text = text.replace('[]', '')
            if mid != tmp_bag_current_mid or idx == num_lines-1:
                # tmp_bag now contains all lines sharing ID tmp_bag_current_mid
                num_contexts = len(tmp_bag)
                sub_bags_dict = {}
                for item in tmp_bag:
                    item_in_doc = item[0]
                    item_text = item[1]
                    item_foss = item[2]
                    if item_in_doc not in sub_bags_dict:
                        sub_bags_dict[item_in_doc] = []
                    sub_bags_dict[item_in_doc].append([item_text, item_foss])
                order = sorted(sub_bags_dict,
                               key=lambda k: len(sub_bags_dict[k]),
                               reverse=True)
                # ↑ keys for sub_bags_dict, ordered for largest bag to smallest

                # min_num_train = math.floor(num_contexts)  # FIXME just a test
                #            FIXME should give 1~few test items per cited doc

                min_num_train = math.floor(num_contexts * 0.8)
                train_tups = []
                test_tups = []
                # TODO: how to do k-fold cross val with this?
                for jdx, sub_bag_key in enumerate(order):
                    sb_tup = sub_bags_dict[sub_bag_key]
                    if len(train_tups) > min_num_train or jdx == len(order)-1:
                        test_tups.extend(sb_tup)
                    else:
                        train_tups.extend(sb_tup)
                test.extend([
                    [tmp_bag_current_mid, tup[0], tup[1]]
                    for tup in test_tups])
                # because we use BOW we can just combine train docs here
                train_text_combined = ' '.join(tup[0] for tup in train_tups)
                train_mids.append(tmp_bag_current_mid)
                train_texts.append(train_text_combined.split())
                train_foss.append([fos for tup in train_tups for fos in tup[1]])
                # reset bag
                tmp_bag = []
                tmp_bag_current_mid = mid
            tmp_bag.append([in_doc, text, cntxt_foss])
    print('loading dictionary')
    dictionary = corpora.Dictionary.load(dict_path)
    num_unique_tokens = len(dictionary.keys())
    print('building corpus')
    corpus = [dictionary.doc2bow(text) for text in train_texts]
    # corpora.MmCorpus.serialize('3s5min5min_corpus.mm', corpus)
    if fos_annot:
        print('preparing FoS model')
        mlb = MultiLabelBinarizer()
        mlb.fit([foss])
        train_foss_matrix = mlb.transform(train_foss)
    print('generating TFIDF model')
    tfidf = models.TfidfModel(corpus)

    # import console
    # console.copen(globals(), locals())

    num_cur = 0
    num_top = 0
    num_top_5 = 0
    num_top_10 = 0
    ndcg_sum_5 = 0
    map_sum_5 = 0
    print('prepring similarities')
    index = similarities.SparseMatrixSimilarity(
                tfidf[corpus],
                num_features=num_unique_tokens)
    print('test set size: {}\n- - - - - - - -'.format(len(test)))
    for tpl in test:
        test_mid = tpl[0]
        test_text = bow_preprocess_string(tpl[1])
        if fos_annot:
            test_foss_vec = mlb.transform([tpl[2]])
            sorted_dot_prods = train_foss_matrix.dot(
                test_foss_vec.transpose()
                ).transpose()[0].argsort()
            fos_ranking = sorted_dot_prods[::-1].tolist()
            # TODO: mby find a way to incorporate dot product value or
            #       FoS level here
        test_bow = dictionary.doc2bow(test_text)
        sims = index[tfidf[test_bow]]
        sims_list = list(enumerate(sims))
        sims_list.sort(key=lambda tup: tup[1], reverse=True)
        bow_ranking = [s[0] for s in sims_list]
        final_ranking = combine_rankings(bow_ranking, fos_ranking)
        rank = len(bow_ranking)  # assign worst possible
        # rank by fos only:
        # sims_list = [[i, 0] for i in fos_top_10]
        for idx, doc_id in enumerate(final_ranking):
            if train_mids[doc_id] == test_mid:
                rank = idx+1
                break
            if idx >= 10:
                break
        dcg = 0
        idcg = 0
        num_rel = 1 + len(adjacent_cit_map[test_mid])
        for i in range(5):
            placement = i+1
            doc_id = final_ranking[i]
            result_mid = train_mids[doc_id]
            if result_mid == test_mid:
                relevance = 1
            elif result_mid in adjacent_cit_map[test_mid]:
                relevance = .5  # FIXME: set to 1
            else:
                relevance = 0
            denom = math.log2(placement + 1)
            dcg_numer = math.pow(2, relevance) - 1
            dcg += dcg_numer / denom
            if placement == 1:
                ideal_rel = 1
            elif placement <= num_rel:
                ideal_rel = .5  # FIXME: set to 1
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
    if len(sys.argv) != 3:
        print(('usage: python3 recommend.py </path/to/docs_file> </path/to/gen'
               'sim_dict>'))
        sys.exit()
    docs_path = sys.argv[1]
    dict_path = sys.argv[2]
    recommend(docs_path, dict_path)
