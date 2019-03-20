import math

AT_K = 10

correct = 'a'
also_ok = ['b', 'c', 'd', 'e']
result = ['-', 'b', '-', '-', 'a', '-', '-', '-', 'c', '-', 'd', 'e']
#          1    2    3    4    5    6    7    8    9   10

ndcg_sums = [0]*AT_K
map_sums = [0]*AT_K
mrr_sums = [0]*AT_K
recall_sums = [0]*AT_K

for idx, mid in enumerate(result):
    if mid == correct:
        rank = idx+1
        break
    if idx >= 10:
       break

dcgs = [0]*AT_K
idcgs = [0]*AT_K
precs = [0]*AT_K
num_rel_at = [0]*AT_K
num_rel = 1 + len(also_ok)
num_rel_at_k = 0
for i in range(AT_K):
    relevant = False
    placement = i+1
    result_mid = result[i]
    if result_mid == correct:
        relevance = 1
        num_rel_at_k += 1
        relevant = True
    elif result_mid in also_ok:
        relevance = .5
        num_rel_at_k += 1
        relevant = True
    else:
        relevance = 0
    num_rel_at[i] = num_rel_at_k
    if relevant:
        precs[i] = num_rel_at_k / placement
    denom = math.log2(placement + 1)
    dcg_numer = math.pow(2, relevance) - 1
    for j in range(i, AT_K):
        dcgs[j] += dcg_numer / denom
    if placement == 1:
        ideal_rel = 1
    elif placement <= num_rel:
        ideal_rel = .5
    else:
        ideal_rel = 0
    idcg_numer = math.pow(2, ideal_rel) - 1
    for j in range(i, AT_K):
        # note this^    we go 0~9, 1~9, 2~9, ..., 9
        idcgs[j] += idcg_numer / denom
print(precs)
print(num_rel_at)
for i in range(AT_K):
    ndcg_sums[i] += dcgs[i] / idcgs[i]
    map_sums[i] += sum(precs[:i+1])/max(num_rel_at[i], 1)
    if rank <= i+1:
        mrr_sums[i] += 1 / rank
        recall_sums[i] += 1


print('NDCG\t{}'.format(['{:.2f}'.format(s) for s in ndcg_sums]))
print('MAP\t{}'.format(['{:.2f}'.format(s) for s in map_sums]))
print('MRR\t{}'.format(['{:.2f}'.format(s) for s in mrr_sums]))
print('Recall\t{}'.format(['{:.2f}'.format(s) for s in recall_sums]))
