import json
import math
import sys

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

with open(sys.argv[1]) as f:
    lines = f.readlines()

# Build test item dict (item->user->judgement) to compare user differences
#   per item.
# Also build user dict (user->array of judgements) to calculate evaluation
#   metrics per user.
items = {}
users = {}
for line in lines:
    timestamp, uid, item_num, json_str = line.split('\u241F')
    judgement_raw = json.loads(json_str.strip())
    judgement = prettify_judgement(item_num, judgement_raw)
    if not item_num in items:
        items[item_num] = {}
    if not uid in items[item_num]:
        items[item_num][uid] = judgement
    if not uid in users:
        users[uid] = []
    users[uid].append(judgement)

for uid, judgements in users.items():
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
