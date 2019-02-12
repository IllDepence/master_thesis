""" Get stats on a CSV of citation contexts.
"""

import os
import math
import sys
import random
import operator
import numpy as np


def stat(docs_path, fos_annot=False):
    """ - foo
    """

    test = []
    train_mids = []
    train_texts = []
    train_foss = []
    foss = []
    num_train_docs = 0
    num_test_docs = 0
    num_train_contexts = 0
    num_test_contexts = 0
    sizes_train_set_bows = []
    lengths_test_set_contexts = []
    tmp_bag = []
    adjacent_cit_map = {}
    nums_contexts = []
    sizes_sub_bags = []

    print('checking file length')
    num_lines = sum(1 for line in open(docs_path))

    print('train/test splitting')
    with open(docs_path) as f:
        for idx, line in enumerate(f):
            if idx == 0:
                tmp_bag_current_mid = line.split('\u241E')[0]
            if idx%10000 == 0:
                print('{}/{} lines'.format(idx, num_lines))
            cntxt_foss = []
            if fos_annot:
                mid, adjacent, in_doc, text, fos_annot = line.split('\u241E')
                cntxt_foss = [f.strip() for f in fos_annot.split('\u241F')
                              if len(f.strip()) > 0]
                foss.extend(cntxt_foss)
            else:
                try:
                    mid, adjacent, in_doc, text = line.split('\u241E')
                except ValueError:
                    # for evaluating w/ FoS data w/o FoS
                    mid, adjacent, in_doc, text, unused = line.split('\u241E')
            # create adjacent map for later use in eval
            if mid not in adjacent_cit_map:
                adjacent_cit_map[mid] = []
            if len(adjacent) > 0:
                adj_cits = adjacent.split('\u241F')
                for adj_cit in adj_cits:
                    if adj_cit not in adjacent_cit_map[mid]:
                        adjacent_cit_map[mid].append(adj_cit)
            # fill texts
            if mid != tmp_bag_current_mid or idx == num_lines-1:
                # tmp_bag now contains all lines sharing ID tmp_bag_current_mid
                num_contexts = len(tmp_bag)
                nums_contexts.append(num_contexts)
                sub_bags_dict = {}
                for item in tmp_bag:
                    item_in_doc = item[0]
                    item_text = item[1]
                    item_foss = item[2]
                    if item_in_doc not in sub_bags_dict:
                        sub_bags_dict[item_in_doc] = []
                    sub_bags_dict[item_in_doc].append([item_text, item_foss])
                if len(sub_bags_dict) < 2:
                    # can't split, reset bag, next
                    tmp_bag = []
                    tmp_bag_current_mid = mid
                    continue
                order = sorted(sub_bags_dict,
                               key=lambda k: len(sub_bags_dict[k]),
                               reverse=True)
                size_sub_bags = []
                for sub_bag in sub_bags_dict.values():
                    size_sub_bags.append(len(sub_bag))
                sizes_sub_bags.append(size_sub_bags)

                min_num_train = math.floor(num_contexts * 0.8)
                train_tups = []
                test_tups = []
                for jdx, sub_bag_key in enumerate(order):
                    sb_tup = sub_bags_dict[sub_bag_key]
                    if len(train_tups) > min_num_train or jdx == len(order)-1:
                        test_tups.extend(sb_tup)
                        num_test_contexts += len(sb_tup)
                    else:
                        num_train_contexts += len(sb_tup)
                        train_tups.extend(sb_tup)
                test.extend([
                    [tmp_bag_current_mid, tup[0], tup[1]]
                    for tup in test_tups])
                num_test_docs += 1
                # because we use BOW we can just combine train docs here
                train_text_combined = ' '.join(tup[0] for tup in train_tups)
                train_mids.append(tmp_bag_current_mid)
                train_texts.append(train_text_combined.split())
                sizes_train_set_bows.append(len(train_text_combined.split()))
                train_foss.append([fos for tup in train_tups for fos in tup[1]])
                num_train_docs += 1
                # reset bag
                tmp_bag = []
                tmp_bag_current_mid = mid
            tmp_bag.append([in_doc, text, cntxt_foss])
    for tup in test:
        lengths_test_set_contexts.append(len(tup[1]))

    print('train docs: {}'.format(num_train_docs))
    print('test docs: {}'.format(num_test_docs))
    print()
    print('train contexts: {}'.format(num_train_contexts))
    print('test contexts: {}'.format(num_test_contexts))
    print()
    print('avg train set bow size: {} (SD {}) ({}~{})'.format(
        np.mean(sizes_train_set_bows), np.std(sizes_train_set_bows),
        np.min(sizes_train_set_bows), np.max(sizes_train_set_bows)))
    print('avg num contexts per cited doc: {} (SD {}) ({}~{})'.format(
        np.mean(nums_contexts), np.std(nums_contexts),
        np.min(nums_contexts), np.max(nums_contexts)))
    print('avg length of test citation contexts: {} (SD {}) ({}~{})'.format(
        np.mean(lengths_test_set_contexts), np.std(lengths_test_set_contexts),
        np.min(lengths_test_set_contexts), np.max(lengths_test_set_contexts)))
    # print('avg # contexts per citing doc: {}'.format(
    #     np.mean(sizes_sub_bags)))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(('usage: python3 dataset_stats.py </path/to/docs_file>'))
        sys.exit()
    docs_path = sys.argv[1]
    stat(docs_path)
