import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

# with open('stepped_match_counts_rel.json') as f:
#     stepped_match_counts = json.load(f)
# with open('conf_match_tups.json') as f:
with open('conf_match_lvl_trips.json') as f:
    tupls = json.load(f)

threshold = 5
# plt.ylim(top=82000)
# stepped_match_counts = [[], []]
# annots = [[], []]
annots = [[], [], [], [], [], []]
good_out = 0
good_in = 0
bad_out = 0
bad_in = 0
for tupl in tupls:
    # conf = tupl[0]
    # match = tupl[1]
    level = tupl[2]
    annots[level].append(tupl[1])
    # if match > 0 and match < .5:
    #     continue
    # if level not in [1, 2] and conf <= threshold:
    #     if match > 0:
    #         good_out += 1
    #     else:
    #         bad_out += 1
    # else:
    #     if match > 0:
    #         good_in += 1
    #     else:
    #         bad_in += 1

    if tupl[1] > 0 and tupl[1] < .5:
        continue
    if tupl[0] <= threshold and level in [4, 5]:
        annots[0].append(tupl[1])
        if tupl[1] > 0:
            good_out += 1
        else:
            bad_out += 1
    else:
        annots[1].append(tupl[1])
        if tupl[1] > 0:
            good_in += 1
        else:
           bad_in += 1

print('    \tin\tout\tΣ')
print('good\t{}\t{}\t{}'.format(good_in, good_out, good_in+good_out))
print('bad\t{}\t{}\t{}'.format(bad_in, bad_out, bad_in+bad_out))
print('Σ\t{}\t{}'.format(good_in+bad_in, good_out+bad_out))

plt.ylabel('#annotations');
plt.xlabel('agreement with MAG FoS');
# for s in range(5):
#     print(s)
#     vals = stepped_match_counts[s]
#     mean = np.mean(vals)
#     std = np.std(vals)
#     min_ = min(vals)
#     max_ = max(vals)
#     print('min: {}'.format(min_))
#     print('max: {}'.format(max_))
#     print('mean: {}'.format(mean))
#     print('std: {}'.format(std))

#     plt.hist(vals, normed=True, bins=30, alpha=.3, label=str(s))
#plt.xlim(right=15)
# plt.hist(stepped_match_counts, bins=25, label=list(range(5)), rwidth=2)
# plt.hist(annots, bins=25, label=['conf <= {}'.format(threshold), 'conf > {}'.format(threshold)], rwidth=2)
plt.hist(annots, bins=25, stacked=True, label=list(range(6)), rwidth=2)
plt.legend(loc='upper right')
plt.show()
