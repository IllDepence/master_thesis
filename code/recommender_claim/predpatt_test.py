""" test predpatt.
"""

import os
import sys
import operator
import datetime
import json
import signal
import re
from predpatt import PredPatt


def signal_handler(signum, frame):
    raise Exception('Timed out!')


def normalize(s):
    s = re.sub('[^\w]', ' ', s)
    s = re.sub('\s+', ' ', s)
    return s.strip().lower()


def foo(docs_path):
    """ - foo
    """

    print('checking file length')
    num_lines = sum(1 for line in open(docs_path))

    print('staring')
    with open(docs_path) as f:
        arg_num_dict = {}
        pred_num_dict = {}
        pp_total_time = 0
        timeouts = 0
        for idx, line in enumerate(f):
            aid, adjacent, in_doc, text = line.split('\u241E')
            t1 = datetime.datetime.now()
            signal.signal(signal.SIGALRM, signal_handler)
            signal.alarm(60)
            try:
                pp = PredPatt.from_sentence(text, cacheable=False)
            except Exception as msg:
                signal.alarm(0)
                timeouts += 1
                continue
            signal.alarm(0)
            t2 = datetime.datetime.now()
            d = t2 - t1
            pp_total_time += d.total_seconds()
            for key, val in pp.event_dict.items():
                pred_norm = normalize(key.text)
                if pred_norm not in pred_num_dict:
                    pred_num_dict[pred_norm] = 0
                pred_num_dict[pred_norm] += 1
                for arg in val.arguments:
                    arg_norm = normalize(arg.phrase())
                    if arg_norm not in arg_num_dict:
                        arg_num_dict[arg_norm] = 0
                    arg_num_dict[arg_norm] += 1
            print('- - - - {}/{} lines - - - -'.format(
                idx, num_lines))
            pp_avg_time = pp_total_time / (idx+1)
            print('# timeouts {}'.format(timeouts))
            print('avg time per context: {:.2f}s'.format(
                pp_avg_time))
            sorted_arg = sorted(arg_num_dict.items(),
                                key=operator.itemgetter(1),
                                reverse=True)
            sorted_pred = sorted(pred_num_dict.items(),
                                 key=operator.itemgetter(1),
                                 reverse=True)
            print('- - top 10 predicates - -')
            for pred, num in sorted_pred[:10]:
                print('{}: {}'.format(num, pred[:30]))
            print('- - top 10 args - -')
            for arg, num in sorted_arg[:10]:
                print('{}: {}'.format(num, arg[:30]))
            if idx%100 == 0:
                with open('arg_num_dict.json', 'w') as f:
                    f.write(json.dumps(arg_num_dict))
                with open('pred_num_dict.json', 'w') as f:
                    f.write(json.dumps(pred_num_dict))
        sorted_arg = sorted(arg_num_dict.items(),
                            key=operator.itemgetter(1),
                            reverse=True)
        sorted_pred = sorted(pred_num_dict.items(),
                             key=operator.itemgetter(1),
                             reverse=True)
        print('top 100 predicates')
        for pred, num in sorted_pred[:100]:
            print('{}: {}'.format(num, pred))
        print('top 100 args')
        for arg, num in sorted_arg[:100]:
            print('{}: {}'.format(num, arg))
        with open('arg_num_dict.json', 'w') as f:
            f.write(json.dumps(arg_num_dict))
        with open('pred_num_dict.json', 'w') as f:
            f.write(json.dumps(pred_num_dict))

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(('usage: python3 ___.py </path/to/docs_file>'))
        sys.exit()
    docs_path = sys.argv[1]
    foo(docs_path)
