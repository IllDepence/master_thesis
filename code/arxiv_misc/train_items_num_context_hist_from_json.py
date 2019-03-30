import json
import os
import sys
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

if len(sys.argv) == 2:
    with open(sys.argv[1]) as f:
        id_val_dict = json.load(f)
    vs = list(id_val_dict.values())
    lim = np.std(vs)*2
    filtered = [v for v in vs if v<=lim]
    ax = plt.figure().gca()
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.hist(filtered, density=True, bins=50)
    plt.show()
else:
    vss = []
    labels = []
    global_lim = 0
    for inp in sys.argv[1:]:
        with open(inp) as f:
            id_val_dict = json.load(f)
        vs = list(id_val_dict.values())
        lim = np.std(vs)
        global_lim = max(lim, global_lim)
        filtered = [v for v in vs if v<=lim]
        vss.append(filtered)
        fn = os.path.split(inp)[-1]
        nm, ext = os.path.splitext(fn)
        labels.append(nm.split('_')[0])
        print(nm)
        print('min: {}'.format(np.min(vs)))
        print('max: {}'.format(np.max(vs)))
        print('mean: {}'.format(np.mean(vs)))
        print('STD: {}'.format(np.std(vs)))
    # ax = plt.figure().gca()
    # ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    # ax.hist(vss, density=True, bins=50)
    # plt.show()
    num_bin = global_lim
    bin_lims = np.linspace(1,global_lim,num_bin+1)
    bin_centers = 0.5*(bin_lims[:-1]+bin_lims[1:])
    bin_widths = bin_lims[1:]-bin_lims[:-1]

    hists = []
    markers = ['^', 'x', 's', '.']
    for vs in vss:
        hist, _ = np.histogram(vs, bins=bin_lims)
        norm = hist/np.sum(hist)
        hists.append(norm)
    for idx, hist in enumerate(hists):
        # plt.bar(bin_centers, hist, width=bin_widths, align='center',
        #         alpha=0.2)
        color = list(mpl.rcParams['axes.prop_cycle'])[idx]['color']
        # plt.plot(bin_centers, hist, linestyle='', marker=markers[idx],
        #          color=color, label=labels[idx], alpha=.8)
        plt.plot(bin_centers, hist, linestyle='-', marker='', alpha=.7, color=color)
    plt.xlabel('number of citation contexts trained on')
    plt.ylabel('percentage of test set items')
    plt.legend(labels)
    plt.show()
