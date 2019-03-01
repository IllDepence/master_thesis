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
from gensim.summarization.bm25 import BM25

SILENT = False


def prind(s):
    if not SILENT:
        print(s)


def better_rank(sims_a, sims_b, train_mids, test_mid):
    sims_list_a = list(enumerate(sims_a))
    sims_list_a.sort(key=lambda tup: tup[1], reverse=True)
    ranking_a = [s[0] for s in sims_list_a]
    sims_list_b = list(enumerate(sims_b))
    sims_list_b.sort(key=lambda tup: tup[1], reverse=True)
    ranking_b = [s[0] for s in sims_list_b]

    if sims_list_b[0][1] == 0:
        return False, 0

    rank_a = len(ranking_a)
    for idx, doc_id in enumerate(ranking_a):
        if train_mids[doc_id] == test_mid:
            rank_a = idx+1
            break
    rank_b = len(ranking_b)
    for idx, doc_id in enumerate(ranking_b):
        if train_mids[doc_id] == test_mid:
            rank_b = idx+1
            break
    if rank_a > rank_b:
        return 1, rank_a - rank_b
    else:
        return 0, rank_b - rank_a


def fos_boost_ranking(bow_ranking, fos_boost, top_dot_prod):
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


def combine_simlists(sl1, sl2, sl3, weights):
    return sl3
    sl = []
    sims_list3 = list(enumerate(sl3))  # FIXME   just playing around
    sims_list3.sort(key=lambda tup: tup[1], reverse=True)
    for i in range(len(sl1)):
        s = sl1[i]
        if sims_list3[0][1] > sims_list3[3][1]*10 and sl3[i] == np.max(sl3):
            s = (s+1)/2
        sl.append(s)
        # sl.append(
        #     (sl1[i]*weights[0])+
        #     (sl2[i]*weights[1])+
        #     (sl3[i]*weights[2])
        #     )
    return sl


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


def recommend(docs_path, dict_path, use_fos_annot=True, pp_dict_path=None,
              lda_preselect=False, combine_train_contexts=True,
              weights=[1, 1, 1]):
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
        prind('loading predpatt dictionary')
        pp_dictionary = corpora.Dictionary.load(pp_dict_path)
        pp_num_unique_tokens = len(pp_dictionary.keys())
        use_predpatt_model = True
        if not combine_train_contexts:
            prind(('usage of predpatt model is not implemented for not'
                   'combining train contexts.\nexiting.'))
            sys.exit()
    else:
        use_predpatt_model = False
        pp_dictionary = None

    prind('checking file length')
    num_lines = sum(1 for line in open(docs_path))

    prind('train/test splitting')
    with open(docs_path) as f:
        for idx, line in enumerate(f):
            if idx == 0:
                tmp_bag_current_mid = line.split('\u241E')[0]
            if idx%10000 == 0:
                prind('{}/{} lines'.format(idx, num_lines))
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
                prind('input file format can not be parsed\nexiting')
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
    prind('loading dictionary')
    dictionary = corpora.Dictionary.load(dict_path)
    num_unique_tokens = len(dictionary.keys())
    prind('building corpus')
    corpus = [dictionary.doc2bow(text) for text in train_texts]

    # import console
    # console.copen(globals(), locals())

    # corpora.MmCorpus.serialize('3s5min5min_corpus.mm', corpus)
    if use_fos_annot:
        prind('preparing FoS model')
        mlb = MultiLabelBinarizer()
        mlb.fit([foss])
        train_foss_matrix = mlb.transform(train_foss)
        train_foss_set_sizes = np.sum(train_foss_matrix, 1)
    prind('generating TFIDF model')
    tfidf = models.TfidfModel(corpus)
    prind('preparing similarities')
    index = similarities.SparseMatrixSimilarity(
                tfidf[corpus],
                num_features=num_unique_tokens)

    # bm25 = BM25(corpus)
    # average_idf = sum(
    #     map(lambda k: float(bm25.idf[k]),
    #         bm25.idf.keys())
    #     ) / len(bm25.idf.keys())

    if lda_preselect:
        orig_index = index.index.copy()

        prind('generating LDA/LSI model')
        lda = LsiModel(tfidf[corpus], id2word=dictionary, num_topics=100)
        # lda = LdaMulticore(tfidf[corpus], id2word=dictionary, num_topics=500)
        # lda = LdaModel(tfidf[corpus], id2word=dictionary, num_topics=10000)
        prind('preparing similarities')
        lda_index = similarities.SparseMatrixSimilarity(
                    lda[tfidf[corpus]],
                    num_features=num_unique_tokens)


    if use_predpatt_model:
        prind('preparing similarities')
        pp_index = similarities.SparseMatrixSimilarity(
            train_ppann,
            num_features=pp_num_unique_tokens)

    num_cur = 0
    num_top = 0
    num_top_5 = 0
    num_top_10 = 0
    ndcg_sum_5 = 0
    map_sum_5 = 0
    prind('test set size: {}\n- - - - - - - -'.format(len(test)))
    foo = 0
    for tpl in test:
        test_mid = tpl[0]
        test_text = bow_preprocess_string(tpl[1])
        if use_fos_annot:
            test_foss_vec = mlb.transform([tpl[2]])
            dot_prods = train_foss_matrix.dot(
                test_foss_vec.transpose()
                ).transpose()[0]
            with np.errstate(divide='ignore',invalid='ignore'):
                fos_sims = np.nan_to_num(dot_prods/train_foss_set_sizes)
            fos_sims_list = list(enumerate(fos_sims))
            fos_sims_list.sort(key=lambda tup: tup[1], reverse=True)
            fos_ranking = [s[0] for s in fos_sims_list]
            # # v hand crafted sliiiiiiight improvement v
            # sorted_dot_prod_ids = train_foss_matrix.dot(
            #     test_foss_vec.transpose()
            #     ).transpose()[0].argsort()
            # fos_ranking = sorted_dot_prod_ids[::-1].tolist()
            # non_zero_dot_prods = len([dp for dp in dot_prods if dp > 0])
            # fos_ranking = fos_ranking[:non_zero_dot_prods]
            # fos_boost = np.where(
            #     dot_prods >= dot_prods.max()-1
            #     )[0].tolist()
            # top_dot_prod = dot_prods[-1]
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

        # bm25_scores = list(enumerate(bm25.get_scores(test_bow, average_idf)))
        # bm25_scores.sort(key=lambda tup: tup[1], reverse=True)
        # bm25_ranking = [s[0] for s in bm25_scores]

        if lda_preselect:
            # translate back from listing in LDA/LSI pick subset to global listing
            bow_ranking = [lda_picks[r] for r in bow_ranking]
        if use_fos_annot and False:
            # # v hand crafted sliiiiiiight improvement v
            final_ranking = fos_boost_ranking(
                bow_ranking, fos_boost, top_dot_prod)
        else:
            final_ranking = bow_ranking
        if not combine_train_contexts:
            seen = set()
            seen_add = seen.add
            final_ranking = [x for x in final_ranking
                     if not (train_mids[x] in seen or seen_add(train_mids[x]))]
        if use_predpatt_model and False:
            # if pp_sims_list[0][1] == 0:
            # if pp_sims_list[0][1] < sims_list[0][1]:
            #     final_ranking = bow_ranking
            # else:
            #     foo += 1
            #     final_ranking = pp_ranking
            sims_comb = combine_simlists(sims, fos_sims, pp_sims, weights)
            sims_list = list(enumerate(sims_comb))
            sims_list.sort(key=lambda tup: tup[1], reverse=True)
            final_ranking = [s[0] for s in sims_list]

        # if top_dot_prod < 1:                # FIXME just a test
        #     continue
        # else:
        #     foo += 1
        #     final_ranking = fos_ranking

        br, delta = better_rank(sims, pp_sims, train_mids, test_mid)
        if br == 1:
            # import console
            # console.copen(globals(), locals())
            # sys.exit()
            # with open('pp_superior.tsv', 'a') as f:
            #    f.write('{}\t{}\t{}\t{}\n'.format(delta, tpl[1], train_text, tpl[3]))
            foo += 1

        # rank by fos only:
        # sims_list = [[i, 0] for i in fos_top_10]

        rank = len(bow_ranking)  # assign worst possible
        for idx, doc_id in enumerate(final_ranking):
            if train_mids[doc_id] == test_mid:
                rank = idx+1
                break
            if idx >= 10:
               break
        # prind('>>>>> rank: {}'.format(rank))  # FIXME remove
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
        prind('- - - - - {}/{} - - - - -'.format(num_cur, len(test)))
        prind('#1: {}'.format(num_top))
        prind('in top 5: {}'.format(num_top_5))
        prind('in top 10: {}'.format(num_top_10))
        prind('ndcg@5: {}'.format(ndcg_sum_5/num_cur))
        prind('map@5: {}'.format(map_sum_5/num_cur))
        prind('foo: {}'.format(foo))  # FIXME remove
    return (ndcg_sum_5/num_cur), (map_sum_5/num_cur)


if __name__ == '__main__':
    if len(sys.argv) not in [3, 4]:
        prind(('usage: python3 recommend.py </path/to/docs_file> </path/to/gen'
               'sim_dict>'))
        sys.exit()
    docs_path = sys.argv[1]
    dict_path = sys.argv[2]
    if len(sys.argv) == 4:
        pp_dict_path = sys.argv[3]
    else:
        pp_dict_path = None

    ndcg_a5, map_a5 = recommend( docs_path,
        dict_path,
        pp_dict_path=pp_dict_path,
        )

    # # linear weights
    # results = []
    # for a in range(0, 110, 15):
    #     for b in range(0, 110, 15):
    #         for c in range(0, 110, 15):
    #             weights = [a/100, b/100, c/100]
    #             ndcg_a5, map_a5 = recommend(
    #                 docs_path,
    #                 dict_path,
    #                 pp_dict_path=pp_dict_path,
    #                 weights=weights
    #                 )
    #             print('{}/{}/{}  ->  {:.5f} | {:.5f}'.format(a/100, b/100, c/100, ndcg_a5, map_a5))
    #             results.append([a/100, b/100, c/100, ndcg_a5, map_a5])
    # results.sort(key=lambda tup: tup[3])
    # print(results)
