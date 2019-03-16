""" Distribution of count of citation contexts per cited doc
"""

import json
import os
import re
import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from matplotlib.colors import LogNorm
from matplotlib.pyplot import figure

font = {'family' : 'normal',
        'weight' : 'normal',
        'size'   : 13}

plt.rc('font', **font)

with open('contexts_per_referece_2018.json') as f:
    citing_counts = json.load(f)

# with open('contexts_per_reference.json') as f:
#     citing_counts = json.load(f)
# print(np.mean(citing_counts))
# print(np.std(citing_counts))
# sys.exit()

fig, ax = plt.subplots(figsize=(8, 3.5))
# citing_count_map = {}
# for citing_count in citing_counts:
#     if citing_count not in citing_count_map:
#         citing_count_map[citing_count] = 0
#     citing_count_map[citing_count] += 1
# 
# x = []
# y = []
# for citing_count in range(max(citing_count_map.keys())):
#     if citing_count in citing_count_map:
#         x.append(citing_count)
#         y.append(citing_count_map[citing_count])

# plt.bar(x, y, align='center', alpha=0.5)
# plt.plot(x, y, 'bo', markersize=1)
# plt.hist(citing_counts, bins=500)
y = sorted(citing_counts, reverse=True)[1:]
x = list(range(len(citing_counts)))[1:]
plt.plot(x, y, '-', markersize=1)
ax.grid(color='lightgray', linestyle='--', linewidth=0.5)
ax.set_xlabel('reference ID')
ax.set_ylabel('citation contexts')
# ax.set_xlabel('document ID')
# ax.set_ylabel('citing documents')

# manual edits
plt.xticks(np.arange(0, 15000001, 5000000))
# plt.xticks(np.arange(0, 2000001, 1000000))
fmt = '{x:,.0f}'
tick = mtick.StrMethodFormatter(fmt)
ax.xaxis.set_major_formatter(tick)
# ax.ticklabel_format(style='plain', scilimits=(0,7), axis='x')

# ax.set_xlabel('citing docs')
# ax.set_ylabel('cited docs')
# plt.xticks(np.arange(0, 100, step=1))
# plt.yticks(np.arange(0, 100000, step=10000))
# plt.xlim(right=3000)
# plt.xlim(left=0)
plt.yscale('log')
# for i, j in zip(x, y):
#     ax.annotate(str(j), xy=(i-0.23,j+1000+(j*0.05)),
#                 color='grey', rotation=90)
plt.tight_layout()

plt.show()
