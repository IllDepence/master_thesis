""" Stats on splits.
"""

import json
import os
import sys
import time

SILENT = False
AT_K = 10


def prind(s):
    if not SILENT:
        print(s)


def stat(docs_path):
    """ - foo
    """

    test = []
    train_mids = []
    test_mids = []
    train_item_num_contexts = []
    train_item_num_context_dict = {}
    tmp_bag = []

    prind('checking file length')
    num_lines = sum(1 for line in open(docs_path))

    # for MAG eval
    mag_id2year = {}
    with open('MAG_CS_en_year_map.csv') as f:
        for line in f:
            pid, year = line.strip().split(',')
            mag_id2year[pid] = int(year)
    # /for MAG eval

    prind('train/test splitting')
    with open(docs_path) as f:
        for idx, line in enumerate(f):
            if idx == 0:
                tmp_bag_current_mid = line.split('\u241E')[0]
            if idx%10000 == 0:
                prind('{}/{} lines'.format(idx, num_lines))
            cntxt_foss = []
            cntxt_ppann = []
            cntxt_nps = []
            # handle varying CSV formats
            vals = line.split('\u241E')
            if len(vals) == 7:
                mid, adjacent, in_doc, text, fos_annot, pp_annot_json, np_annot = vals
            else:
                prind('input file format can not be parsed\nexiting')
                sys.exit()
            # create adjacent map for later use in eval
            # fill texts
            if mid != tmp_bag_current_mid or idx == num_lines-1:
                # tmp_bag now contains all lines sharing ID tmp_bag_current_mid
                num_contexts = len(tmp_bag)
                sub_bags_dict = {}
                for item in tmp_bag:
                    item_in_doc = item[0]
                    if item_in_doc not in sub_bags_dict:
                        sub_bags_dict[item_in_doc] = []
                    sub_bags_dict[item_in_doc].append(
                        ['x']
                        )
                if len(sub_bags_dict) < 2:
                    # can't split, reset bag, next
                    tmp_bag = []
                    tmp_bag_current_mid = mid
                    continue
                order = sorted(sub_bags_dict,
                               key=lambda k: len(sub_bags_dict[k]),
                               reverse=True)
                # ↑ keys for sub_bags_dict, ordered for largest bag to smallest

                train_tups = []
                test_tups = []
                for jdx, sub_bag_key in enumerate(order):
                    sb_tup = sub_bags_dict[sub_bag_key]
                    # if sub_bag_key[:2] == '17':  # FIXME time split arXiv
                    # if mag_id2year[sub_bag_key] > 2017:  # FIXME time split MAG
                    # if sub_bag_key[1:3] == '06':  # FIXME time split ACL
                    try:
                        refseer_year = int(sub_bag_key.split('_')[0])
                    except ValueError:
                        print('unexpected citing doc year for {}'.format(sub_bag_key))
                        refseer_year = 0
                    if refseer_year > 2011:  # FIXME time split refseer
                        test_tups.extend(sb_tup)
                    else:
                        train_tups.extend(sb_tup)
                if len(test_tups) > 0:
                    test_mids.append(tmp_bag_current_mid)
                test.extend(
                    [
                        [tmp_bag_current_mid]
                        for tup in test_tups
                    ])
                # combine train contexts per cited doc
                train_item_num_contexts.append(len(train_tups))
                if len(train_tups) > 0:
                    train_item_num_context_dict[tmp_bag_current_mid] = len(train_tups)
                train_mids.append(tmp_bag_current_mid)
                # reset bag
                tmp_bag = []
                tmp_bag_current_mid = mid
            tmp_bag.append([in_doc])
    print('number of candidates to rank: {}'.format(len(train_mids)))
    print('number of test set items: {}'.format(len(test)))
    print('trained for {} cited docs (rankable candidates)'.format(len(train_item_num_context_dict)))
    print('will test for {} of those'.format(len(set(test_mids))))
    # with open('train_item_num_contexts_{}.json'.format(str(int(time.time()))), 'w') as f:
    #     f.write(json.dumps((train_item_num_contexts)))
    # with open('train_item_num_context_dict_{}.json'.format(str(int(time.time()))), 'w') as f:
    #     f.write(json.dumps((train_item_num_context_dict)))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        prind('usage: python3 eval_split_stats.py </path/to/docs_file>')
        sys.exit()
    docs_path = sys.argv[1]

    stat(docs_path)
