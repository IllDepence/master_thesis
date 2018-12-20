import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

# with open('annot_dist_lvl_vals.json') as f:
# with open('annot_dist_conf_vals.json') as f:
# with open('annot_dist_qual_vals.json') as f:
with open('conf_match_tups.json') as f:
    tupls = json.load(f)

x = []
y = []
for tupl in tupls:
    # if tupl[1] <= 300 and tupl[0] <= 1000:
    # if tupl[1] <= 500 and tupl[1] >= 20:
    # if tupl[0] <= 1:
    if tupl[0] > 5.0 and tupl[0] <= 30:
        x.append(tupl[0])
        y.append(tupl[1])

plt.xlabel('confidence values')
plt.ylabel('agreement with MAG')
# plt.ylabel('annotation level')
heatmap, xedges, yedges = np.histogram2d(x, y, bins=(50, 11))
# heatmap, xedges, yedges = np.histogram2d(x, y, bins=(50))
extent = [xedges[0], xedges[-1], yedges[0], yedges[-1]]
# plt.imshow(heatmap.T, extent=extent, origin='lower', norm=LogNorm(), aspect='auto')
plt.imshow(heatmap.T, extent=extent, origin='lower', aspect='auto')
plt.colorbar()

# plt.scatter(x, y, alpha=0.5)
plt.show()
