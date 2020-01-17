import json
import sys
from scipy import stats, mean
from mlxtend.evaluate import permutation_test

with open(sys.argv[1]) as f:
    pairs = json.load(f)

scores_baseline = [x[0] for x in pairs]
scores_new = [x[1] for x in pairs]

print('mean baseline: {}'.format(mean(scores_baseline)))
print('mean new: {}'.format(mean(scores_new)))

t, p = stats.ttest_rel(scores_baseline, scores_new)

print()
print('# # # Student\'t t-test # # #')
print('t-statistic: {}'.format(t))
print('Two-sided p-value: {}'.format(p))

perm_p = permutation_test(scores_baseline, scores_new,
                           method='approximate',
                           num_rounds=10000,
                           seed=0)
print()
print('# # # Permutation test # # #')
print('Two-sided p-value (alpha=0.01): {}'.format(perm_p))

# - - - - -

num_same = 0
num_better = 0
num_worse = 0
for pair in pairs:
    if pair[1] > pair[0]:
        num_better += 1
    elif pair[0] > pair[1]:
        num_worse += 1
    else:
        num_same += 1

print()
print('#better: {}'.format(num_better))
print('#same: {}'.format(num_same))
print('#worse: {}'.format(num_worse))
