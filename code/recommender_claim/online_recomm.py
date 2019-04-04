""" Recommend from saved model in online setting
"""

import json
import os
import re
from gensim import corpora, models, similarities
from gensim.matutils import corpus2csc, Sparse2Corpus
from util import bow_preprocess_string
from predpatt_parse_contexts import build_sentence_representation as build_pp_rep
from scipy.sparse import csc_matrix

MAINCITS_PATT = re.compile(r'((CIT , )*MAINCIT( , CIT)*)')
CITS_PATT = re.compile(r'(((?<!MAIN)CIT , )*(?<!MAIN)CIT( , (?<!MAIN)CIT)*)')


def sims2ranking(sims, top=5):
    sims_list = list(enumerate(sims))
    sims_list.sort(key=lambda tup: tup[1], reverse=True)
    if sims_list[0][1] == 0:
        return []
    ranking = [s[0] for s in sims_list]
    ranking_cut = ranking[:top]
    return [id_list[r] for r in ranking_cut]


def merge_citation_token_lists(s):
    s = MAINCITS_PATT.sub('MAINCIT', s)
    s = CITS_PATT.sub('CIT', s)
    return s


def combine_simlists(sl1, sl2, weights):
    sl = []
    for i in range(len(sl1)):
        sl.append(
            (sl1[i]*weights[0])+
            (sl2[i]*weights[1])
            )
    return sl


def build_np_rep(text, np_dict, max_np_len):
    text = merge_citation_token_lists(text)
    np_rep = []
    try:
        pre, post = text.split('MAINCIT')
    except ValueError:
        # data with no MAINCIT in context, assume sentence end
        pre = text
        post = ''
    words = [re.sub('[^a-zA-Z0-9-]', ' ', w).strip()
             for w in pre.split()]
    # fixed position, so only go through sizes
    for i in range(max_np_len):
        chunk_size = max_np_len - i  # counting down
        if chunk_size < 2:
            break
        if len(words) < chunk_size:
            continue
        chunk = ' '.join(words[-chunk_size:])
        try:
            np_dict.token2id[chunk]
            in_dict = True
        except KeyError:
            in_dict = False
        if in_dict:
            np_rep.append(chunk)
    return np_rep


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


def mid2recomm(mid, mid2info):
    info = mid2info[mid]
    return [mid, info['title'], info['year'],
            info['citcount'], info['abstract']]


# bow
bow_dict_fn = 'online_eval_model/items_CSall_1s_5mindoc_5mincont_wPP_3.1_wNP_both.dict'
bow_model_fn = 'online_eval_model/arXivCS_bow_model.tfidf'
bow_index_fn = 'online_eval_model/arXivCS_bow_index.idx'
# pp
pp_dict_fn = 'online_eval_model/items_CSall_1s_5mindoc_5mincont_wPP_3.1_wNP_both_PPterms.dict'
pp_model_fn = 'online_eval_model/arXivCS_pp_model.tfidf'
pp_index_fn = 'online_eval_model/arXivCS_pp_index.idx'
# np
np_dict_fn = 'online_eval_model/arxiv_allNPs_until20180830_countGt2_cleaned.dict'
np_index_fn = 'online_eval_model/arXivCS_npmarker_index.idx'
# recomm
id_list_fn = 'online_eval_model/arXivCS_ID_list.json'
mid2info_fn = 'online_eval_model/arxivCS_mid2info.json'
# IPC
pipe_query_fn = 'arXivCS_query_fifo'
pipe_recomm_fn = 'arXivCS_recomm_fifo'

print('loading models')
bow_dictionary = corpora.Dictionary.load(bow_dict_fn)
pp_dictionary = corpora.Dictionary.load(pp_dict_fn)
np_dictionary = corpora.Dictionary.load(np_dict_fn)
np_num_unique_tokens = len(np_dictionary.keys())
max_np_len = 0
for np in np_dictionary.values():
    max_np_len = max(max_np_len, len(np.split()))
bow_index = similarities.SparseMatrixSimilarity.load(bow_index_fn)
pp_index = similarities.SparseMatrixSimilarity.load(pp_index_fn)
np_index = similarities.SparseMatrixSimilarity.load(np_index_fn)
bow_tfidf = models.TfidfModel.load(bow_model_fn)
pp_tfidf = models.TfidfModel.load(pp_model_fn)
with open(id_list_fn) as f:
    id_list = json.load(f)
print('done')
print('loading MAG info')
with open(mid2info_fn) as f:
    mid2info = json.load(f)
print('done')

print('initializing PredPatt')
pp_warmup = ('Huang et al. MAINCIT used an online active SVM'
             '(LASVM) to boost the speed of SVM classifier.')
pp_tuples, _ = build_pp_rep(pp_warmup)
print('done')

if not os.path.exists(pipe_query_fn):
    _foo = os.mkfifo(pipe_query_fn)
if not os.path.exists(pipe_recomm_fn):
    _bar = os.mkfifo(pipe_recomm_fn)

print('waiting for flask app')
pipe_in = open(pipe_query_fn, 'r')
pipe_out = os.open(pipe_recomm_fn, os.O_WRONLY)

while True:
    print('waiting for query')
    input_text = pipe_in.readline()
    print('recommending ...')
    input_text = input_text.strip()
    input_text = input_text.replace('[]', ' MAINCIT ')

    # try:
    prep_text = bow_preprocess_string(input_text)
    test_bow = bow_dictionary.doc2bow(prep_text)
    bow_sims = bow_index[bow_tfidf[test_bow]]
    bow_ranking = sims2ranking(bow_sims)

    pp_tuples, _ = build_pp_rep(input_text)
    pp_rep = sum_weighted_term_lists(pp_tuples, pp_dictionary)
    pp_sims = pp_index[pp_tfidf[pp_rep]]
    comb_sims = combine_simlists(bow_sims, pp_sims, [2, 1])
    pp_ranking = sims2ranking(comb_sims)

    np_rep = build_np_rep(input_text, np_dictionary, max_np_len)
    np_ranking = []
    if len(np_rep) > 0:
        np_bow = np_dictionary.doc2bow(np_rep)
        if np_bow:
            np_sims = np_index[np_bow]
            np_ranking = sims2ranking(np_sims)
    msg = '{}\n'.format(json.dumps(
        [
            [mid2recomm(mid, mid2info) for mid in bow_ranking],
            [mid2recomm(mid, mid2info) for mid in pp_ranking],
            [mid2recomm(mid, mid2info) for mid in np_ranking]
        ]))
    # except:
    #     msg = '[[],[],[]]\n'

    os.write(pipe_out, msg.encode())
