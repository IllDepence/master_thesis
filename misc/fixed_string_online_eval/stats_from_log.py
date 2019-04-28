import json
import math
import sys
from operator import itemgetter
from nltk.metrics.agreement import AnnotationTask
from nltk.metrics import ConfusionMatrix

np_not_applicable = [0, 1, 4, 5, 6, 7, 8, 9, 10, 12, 14, 15, 16, 17, 18, 21, 23,
27, 28, 30, 31, 32, 33, 35, 36, 39, 41, 45, 47, 48, 49, 51, 52, 55, 56, 57, 58,
59, 61, 62, 63, 64, 71, 72, 74, 77, 78, 80, 82, 84, 85, 86, 88, 89, 92, 93, 94,
95, 96, 98, 101, 102, 103, 104, 105, 106, 107, 109, 111, 114, 115, 116, 117,
118, 119, 120, 121, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135,
136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151,
152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 168, 170,
172, 173, 175, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189,
190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205,
206, 209, 210, 212, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224,
225, 227, 228, 229, 230, 231, 233, 234, 235, 236, 237, 238, 239, 241, 242, 243,
247, 248, 249, 250, 252, 254, 255, 256, 257, 258, 259, 263, 264, 265, 266, 268,
269, 271, 272, 273, 276, 277, 278, 279, 282, 283, 284, 285, 286, 287, 288, 289,
292, 293, 294, 295, 296, 297, 298, 300, 302, 303, 304, 305, 306, 307, 308, 309,
311, 312, 313, 314, 316, 318, 319, 320, 321, 322, 323, 326, 328, 329, 330, 331,
334, 335, 337, 338, 339, 340, 341, 344, 345, 346, 347, 349, 352, 353, 354, 356,
357, 359, 361, 362, 364, 365, 366, 368, 369, 371, 372, 373, 377, 378, 379, 382,
383, 384, 388, 389, 390, 391, 393, 394, 396, 397, 398, 399, 401, 402, 403, 404,
407, 408, 409, 410, 411, 412, 414]


def prettify_judgement(item_num, j):
    """ Change recorded data from web form output into nicer format.
    """

    if type(j) == str:
        return j
    nj = {
        'cit_type': j.get('cit_type', '<not selected>'),
        'author_in_context': j.get('author_name', 'off'),
        'syntactic': j.get('syntactical', 'off')
        }
    models = ['bow', 'pp']
    bow = [False]*5
    pp = [False]*5
    model_arrs = [bow, pp]
    if int(item_num) not in np_not_applicable:
        models.append('np')
        np = [False]*5
        model_arrs.append(np)
    else:
        np = None
    for mi, model in enumerate(models):
        for idx in [1, 2, 3, 4, 5]:
            if j.get('{}{}'.format(model, idx), False):
                model_arrs[mi][idx-1] = True
    nj['bow'] = bow
    nj['pp'] = pp
    nj['np'] = np
    return nj


def pjudgement_to_nltk_annot_task(uid, item_num, pjudgement, **kwargs):
    """ Transform prettyfied judgement into NLTK AnnotationTask fromat.
        http://www.nltk.org/api/nltk.metrics.html

        Possible kwargs:
            only_key: cit_type / author_in_context / syntactic
            only_relevance: True / False
    """

    if type(pjudgement) == str:
        return [(uid, item_num, pjudgement)]

    task_items = []
    keys = ['cit_type', 'author_in_context', 'syntactic']
    if kwargs.get('only_key', False):
        keys = [kwargs.get('only_key')]
    elif kwargs.get('only_relevance', False):
        keys = []
    for key in keys:
        task_items.append((
            uid,
            '{}{}'.format(item_num, key),
            pjudgement[key]
            ))
    if kwargs.get('only_key', False):
        return task_items
    models = ['bow', 'pp']
    if pjudgement['np'] != None:
        models.append('np')
    for model in models:
        for rank, rel in enumerate(pjudgement[model]):
            task_items.append((
                uid,
                '{}{}{}'.format(item_num, model, rank),
                rel
                ))
    return task_items


def align_annot_task(tup_arr):
    """ Items passed by at least one author can not be compared to judgements
        performed by others. The aligned task is therefore the intersection of
        items not passed.
    """

    aligned = []
    num_raters = len(set([t[0] for t in tup_arr]))
    tup_arr.sort(key=itemgetter(1))
    for key in set([t[1] for t in tup_arr]):
        ratings = [t for t in tup_arr if t[1] == key]
        if len(ratings) == num_raters:
            if ratings[0][2] not in ['undecidable', 'pass', 'broken']:
                aligned.extend(ratings)
    return aligned


lines = []
for in_file in sys.argv[1:]:
    with open(in_file) as f:
        lines += f.readlines()

# Build test item dict (item->user->judgement) to compare user differences
#   per item.
# Also build user dict (user->array of judgements) to calculate evaluation
#   metrics per user.
items = {}
users = {}
annot_task_all = []
annot_task_type = []
annot_task_auth = []
annot_task_synt = []
annot_task_rel = []
for line in lines:
    timestamp, uid, item_num, json_str = line.split('\u241F')
    judgement_raw = json.loads(json_str.strip())
    judgement = prettify_judgement(item_num, judgement_raw)
    annot_task_all += pjudgement_to_nltk_annot_task(
        uid,
        item_num,
        judgement)
    annot_task_type += pjudgement_to_nltk_annot_task(
        uid,
        item_num,
        judgement,
        only_key='cit_type')
    annot_task_auth += pjudgement_to_nltk_annot_task(
        uid,
        item_num,
        judgement,
        only_key='author_in_context')
    annot_task_synt += pjudgement_to_nltk_annot_task(
        uid,
        item_num,
        judgement,
        only_key='syntactic')
    annot_task_rel += pjudgement_to_nltk_annot_task(
        uid,
        item_num,
        judgement,
        only_relevance=True)
    if not item_num in items:
        items[item_num] = {}
    if not uid in items[item_num]:
        items[item_num][uid] = judgement
    if not uid in users:
        users[uid] = []
    users[uid].append(judgement)

task_dict = {
    'all': annot_task_all,
    'type': annot_task_type,
    'auth': annot_task_auth,
    'synt': annot_task_synt,
    'rel': annot_task_rel
    }

for label, task in task_dict.items():
    if len(set([t[0] for t in task])) != 2:
        # number of raters != 2
        continue
    ata = align_annot_task(task)
    ata.sort(key=itemgetter(1))
    t = AnnotationTask(ata)
    same = 0
    diff = 0
    for key in set([t[1] for t in ata]):
        r1, r2 = [t for t in ata if t[1] == key]
        if r1[2] == r2[2]:
            same += 1
        else:
            diff += 1
    print('- - - {} - - -'.format(label))
    print('Agreement on: {}/{}'.format(same, same+diff))
    print('Average observed agreement: {}'.format(t.avg_Ao()))
    print('Krippendorff\'s alpha: {}'.format(t.alpha()))

if len(set([t[0] for t in task])) == 2:
    # number of raters = 2
    type_arr1 = []
    type_arr2 = []
    att = align_annot_task(annot_task_type)
    att.sort(key=itemgetter(1))
    for key in set([t[1] for t in att]):
        r1, r2 = [t for t in att if t[1] == key]
        type_arr1.append(r1[2])
        type_arr2.append(r2[2])
    cm = ConfusionMatrix(type_arr1, type_arr2)

    types = ['claim', 'ne', 'example', 'other']
    print()
    print('\t'.join([''] + types))
    for tx in types:
        vals = []
        for ty in types:
            vals.append(cm[tx, ty])
        print('\t'.join([tx] + [str(v) for v in vals]))

    users_sep = list(users.items())
    users_both = [('all', users_sep[0][1]+users_sep[1][1])]
    users_comb = users_sep + users_both
else:
    users_comb = list(users.items())

for uid, judgements in users_comb:
    num_judgements = 0
    print()
    print('### user: {} ###'.format(uid))
    print('#')
    print('## items judged: {}'.format(len(judgements)))
    num_pass = 0
    num_undecidable = 0
    num_broken = 0
    num_with_author = 0
    num_syntactic = 0
    num_type = {}
    model_labels = ['bow', 'pp', 'np']
    metrics = {}
    for ml in model_labels:
        metrics[ml] = {
            'ndcg_sum': 0,
            'map_sum': 0,
            'mrr_sum': 0,
            'recall_sum': 0
            }
    remaining = 0
    remaining_np = 0
    for j in judgements:
        if j == 'pass':
            num_pass += 1
        elif j == 'undecidable':
            num_undecidable += 1
        elif j == 'broken':
            num_broken += 1
        else:
            # if j['cit_type'] != 'claim':
            #     continue
            remaining += 1
            if j['np'] != None:
                remaining_np += 1
            if j['author_in_context'] == 'on':
                num_with_author += 1
            if j['syntactic'] == 'on':
                num_syntactic += 1
            if j['cit_type'] not in num_type:
                num_type[j['cit_type']] = 0
            num_type[j['cit_type']] += 1
            # determine number of "possible" relevant items
            #
            # because we can't know how many relevant items there are, we take
            # a minimum of 1 and if there are >1 Trues in the judgements of any
            # of the 3 models we take the maxum number of Trues
            num_relevant = 1
            for ml in model_labels:
                if j[ml] == None:
                    continue
                num_judgements += 5
                ts = len([i for i in j[ml] if i])  # number of Trues
                num_relevant = max(ts, num_relevant)
            # go through models and their relevance judgements
            for ml in model_labels:
                if j[ml] == None:
                    continue
                # Recall
                ts = len([i for i in j[ml] if i])  # number of Trues
                if True in j[ml]:
                    metrics[ml]['recall_sum'] += ts/num_relevant
                # MRR
                for rank, relevant in enumerate(j[ml]):
                    if relevant:
                        metrics[ml]['mrr_sum'] += 1/(rank+1)
                        break
                # MAP
                map_tmp_sum = 0
                map_tmp_rel = 0
                if ts > 0:
                    for rank, relevant in enumerate(j[ml]):
                        if relevant:
                            map_tmp_rel += 1
                            map_tmp_sum += map_tmp_rel/(rank+1)
                    metrics[ml]['map_sum'] += map_tmp_sum/ts
                # NDCG
                dcg_tmp_sum = 0
                idcg_tmp_sum = 0
                if ts > 0:
                    for rank, relevant in enumerate(j[ml]):
                        denom = math.log2((rank+1) + 1)
                        relevance = 0
                        i_relevance = 0
                        if relevant:
                            relevance = 1
                        if (rank+1) <= ts:
                            i_relevance = 1
                        dcg_numer = math.pow(2, relevance) - 1
                        idcg_numer = math.pow(2, i_relevance) - 1
                        dcg_tmp_sum += dcg_numer / denom
                        idcg_tmp_sum += idcg_numer / denom
                    metrics[ml]['ndcg_sum'] += dcg_tmp_sum/idcg_tmp_sum
    print('#')
    print('# passed: {}'.format(num_pass))
    print('# undecidable: {}'.format(num_undecidable))
    print('# broken: {}'.format(num_broken))
    print('#')
    print('## remaining: {}'.format(remaining))
    print('## number of judgements: {}'.format(num_judgements))
    print('#')
    print('# with author: {}'.format(num_with_author))
    print('# syntactic: {}'.format(num_syntactic))
    print('#')
    for label, num in num_type.items():
        print('# type {}: {}'.format(label, num))
    print('#')
    for ml in model_labels:
        if ml == 'np':
            num_items = remaining_np
        else:
            num_items = remaining
        print(('# {} Recall: {:.2f} | MRR: {:.2f} '
               '| MAP: {:.2f} | NDCG: {:.2f}').format(
            ml,
            metrics[ml]['recall_sum']/num_items,
            metrics[ml]['mrr_sum']/num_items,
            metrics[ml]['map_sum']/num_items,
            metrics[ml]['ndcg_sum']/num_items
            ))
