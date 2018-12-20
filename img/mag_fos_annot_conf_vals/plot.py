import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

# with open('stepped_match_counts_rel.json') as f:
#     stepped_match_counts = json.load(f)
with open('conf_match_tups.json') as f:
    tupls = json.load(f)

stepped_match_counts = [[], []]
for threshold in range(5, 16):
    for tupl in tupls:
        if tupl[0] <= threshold:
            stepped_match_counts[0].append(tupl[1])
        else:
            stepped_match_counts[1].append(tupl[1])

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
    plt.hist(stepped_match_counts, bins=25, label=['conf <= {}'.format(threshold), 'conf > {}'.format(threshold)], rwidth=2)
    plt.legend(loc='upper right')
    plt.show()
