""" Recommend using TFIDF/BOW approach.
"""

import json
import math
import operator
import os
import random
import sys
import numpy as np
from gensim import corpora, models, similarities
from util import bow_preprocess_string
from scipy.sparse import csc_matrix
from sklearn.preprocessing import MultiLabelBinarizer
from gensim.models.ldamulticore import LdaMulticore
# from gensim.models.ldamodel import LdaModel
from gensim.models import LsiModel
from gensim.matutils import corpus2csc, Sparse2Corpus


def combine_rankings(bow_ranking, fos_boost, top_dot_prod):
    if top_dot_prod < 1:
        return bow_ranking
    point_dic = {}
    for i in range(len(bow_ranking)):
        points = len(bow_ranking) - i
        if bow_ranking[i] not in point_dic:
            point_dic[bow_ranking[i]] = 0
        point_dic[bow_ranking[i]] += points
    for boost in fos_boost:
        point_dic[boost] += 1.1
    comb = sorted(point_dic.items(), key=operator.itemgetter(1), reverse=True)
    return [c[0] for c in comb]


def sum_weighted_term_lists(wtlist, dictionary):
    if len(wtlist) == 0:
        return []
    term_vecs = []
    for weight, terms in wtlist:
        term_vec_raw = dictionary.doc2bow(terms)
        term_vec = [(term_id, weight*val) for term_id, val in term_vec_raw]
        term_vecs.append(term_vec)
    # make into numpy matrix for convenience
    term_matrix = corpus2csc(term_vecs)
    # calculate sum
    sum_vec = Sparse2Corpus(
        csc_matrix(term_matrix.sum(1))
        )[0]
    return sum_vec


def recommend(docs_path, dict_path, use_fos_annot=False, pp_dict_path=None,
              lda_preselect=False, combine_train_contexts=True):
    """ - foo
    """

    test = []
    train_mids = []
    train_texts = []
    train_foss = []
    train_ppann = []
    foss = []
    tmp_bag = []
    adjacent_cit_map = {}

    if pp_dict_path:
        print('loading predpatt dictionary')
        pp_dictionary = corpora.Dictionary.load(pp_dict_path)
        pp_num_unique_tokens = len(pp_dictionary.keys())
        use_predpatt_model = True
        if not combine_train_contexts:
            print(('usage of predpatt model is not implemented for not'
                   'combining train contexts.\nexiting.'))
            sys.exit()
    else:
        use_predpatt_model = False
        pp_dictionary = None

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
            cntxt_ppann = []
            # handle varying CSV formats
            vals = line.split('\u241E')
            if len(vals) == 4:
                mid, adjacent, in_doc, text = vals
            elif len(vals) == 5:
                if use_predpatt_model:
                    mid, adjacent, in_doc, text, pp_annot_json = vals
                else:
                    mid, adjacent, in_doc, text, fos_annot = vals
            elif len(vals) == 6:
                mid, adjacent, in_doc, text, fos_annot, pp_annot_json = vals
            else:
                print('input file format can not be parsed\nexiting')
                sys.exit()
            if len(vals) in [5, 6] and use_fos_annot:
                cntxt_foss = [f.strip() for f in fos_annot.split('\u241F')
                              if len(f.strip()) > 0]
                foss.extend(cntxt_foss)
            if use_predpatt_model:
                cntxt_ppann = json.loads(pp_annot_json)
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
                    item_ppann = item[3]
                    if item_in_doc not in sub_bags_dict:
                        sub_bags_dict[item_in_doc] = []
                    sub_bags_dict[item_in_doc].append(
                        [item_text, item_foss, item_ppann]
                        )
                if len(sub_bags_dict) < 2:
                    # can't split, reset bag, next
                    tmp_bag = []
                    tmp_bag_current_mid = mid
                    continue
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
                test.extend(
                    [
                        [tmp_bag_current_mid, tup[0], tup[1],
                         sum_weighted_term_lists(tup[2], pp_dictionary)
                        ]
                    for tup in test_tups
                    ])
                # because we use BOW we can just combine train docs here
                if combine_train_contexts:
                    train_text_combined = ' '.join(tup[0] for tup in train_tups)
                    train_mids.append(tmp_bag_current_mid)
                    train_texts.append(train_text_combined.split())
                    train_foss.append(
                        [fos for tup in train_tups for fos in tup[1]]
                        )
                    train_ppann.append(
                        sum_weighted_term_lists(
                            sum([tup[2] for tup in train_tups], []),
                            pp_dictionary
                            )
                        )
                else:
                    for tup in train_tups:
                        train_mids.append(tmp_bag_current_mid)
                        train_texts.append(tup[0].split())
                        train_foss.append([fos for fos in tup[1]])
                # reset bag
                tmp_bag = []
                tmp_bag_current_mid = mid
            tmp_bag.append([in_doc, text, cntxt_foss, cntxt_ppann])
    print('loading dictionary')
    dictionary = corpora.Dictionary.load(dict_path)
    num_unique_tokens = len(dictionary.keys())
    print('building corpus')
    corpus = [dictionary.doc2bow(text) for text in train_texts]

    # import console
    # console.copen(globals(), locals())

    # corpora.MmCorpus.serialize('3s5min5min_corpus.mm', corpus)
    if use_fos_annot:
        print('preparing FoS model')
        mlb = MultiLabelBinarizer()
        mlb.fit([foss])
        train_foss_matrix = mlb.transform(train_foss)
    print('generating TFIDF model')
    tfidf = models.TfidfModel(corpus)
    print('preparing similarities')
    index = similarities.SparseMatrixSimilarity(
                tfidf[corpus],
                num_features=num_unique_tokens)

    if lda_preselect:
        orig_index = index.index.copy()

        print('generating LDA/LSI model')
        lda = LsiModel(tfidf[corpus], id2word=dictionary, num_topics=100)
        # lda = LdaMulticore(tfidf[corpus], id2word=dictionary, num_topics=500)
        # lda = LdaModel(tfidf[corpus], id2word=dictionary, num_topics=10000)
        print('preparing similarities')
        lda_index = similarities.SparseMatrixSimilarity(
                    lda[tfidf[corpus]],
                    num_features=num_unique_tokens)


    if use_predpatt_model:
        print('preparing similarities')
        pp_index = similarities.SparseMatrixSimilarity(
            train_ppann,
            num_features=pp_num_unique_tokens)

    num_cur = 0
    num_top = 0
    num_top_5 = 0
    num_top_10 = 0
    ndcg_sum_5 = 0
    map_sum_5 = 0
    print('test set size: {}\n- - - - - - - -'.format(len(test)))
    foo = 0
    for tpl in test:
        test_mid = tpl[0]
        test_text = bow_preprocess_string(tpl[1])
        if use_fos_annot:
            test_foss_vec = mlb.transform([tpl[2]])
            sorted_dot_prod_ids = train_foss_matrix.dot(
                test_foss_vec.transpose()
                ).transpose()[0].argsort()
            sorted_dot_prods = train_foss_matrix.dot(
                test_foss_vec.transpose()
                ).transpose()[0]
            fos_ranking = sorted_dot_prod_ids[::-1].tolist()
            fos_boost = np.where(
                sorted_dot_prods >= sorted_dot_prods.max()-1
                )[0].tolist()
            top_dot_prod = sorted_dot_prods[-1]
        if use_predpatt_model:
            pp_sims = pp_index[tpl[3]]
            pp_sims_list = list(enumerate(pp_sims))
            pp_sims_list.sort(key=lambda tup: tup[1], reverse=True)
            pp_ranking = [s[0] for s in pp_sims_list]
        test_bow = dictionary.doc2bow(test_text)
        if lda_preselect:
            # pre select in LDA/LSI space
            lda_sims = lda_index[lda[tfidf[test_bow]]]
            lda_sims_list = list(enumerate(lda_sims))
            lda_sims_list.sort(key=lambda tup: tup[1], reverse=True)
            lda_ranking = [s[0] for s in lda_sims_list]
            lda_picks = lda_ranking[:1000]
            index.index = orig_index[lda_picks]
        sims = index[tfidf[test_bow]]
        sims_list = list(enumerate(sims))
        sims_list.sort(key=lambda tup: tup[1], reverse=True)
        bow_ranking = [s[0] for s in sims_list]
        if lda_preselect:
            # translate back from listing in LDA/LSI pick subset to global listing
            bow_ranking = [lda_picks[r] for r in bow_ranking]
        if use_fos_annot:
            final_ranking = combine_rankings(
                bow_ranking, fos_boost, top_dot_prod)
        else:
            final_ranking = bow_ranking
        if not combine_train_contexts:
            seen = set()
            seen_add = seen.add
            final_ranking = [x for x in final_ranking
                     if not (train_mids[x] in seen or seen_add(train_mids[x]))]
        if pp_sims_list[0][1] == 0:
            final_ranking = bow_ranking
        else:
            final_ranking = pp_ranking
        # if top_dot_prod < 1:                # FIXME just a test
        #     continue
        # else:
        #     foo += 1
        #     final_ranking = fos_ranking
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
        print('foo: {}'.format(foo))  # FIXME remove


if __name__ == '__main__':
    if len(sys.argv) not in [3, 4]:
        print(('usage: python3 recommend.py </path/to/docs_file> </path/to/gen'
               'sim_dict>'))
        sys.exit()
    docs_path = sys.argv[1]
    dict_path = sys.argv[2]
    if len(sys.argv) == 4:
        pp_dict_path = sys.argv[2]
    else:
        pp_dict_path = None
    recommend(docs_path, dict_path, pp_dict_path=pp_dict_path)
