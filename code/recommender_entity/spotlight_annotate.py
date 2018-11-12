import json
import os
import requests
import sys
import time
import spotlight

ANNOT_URL = 'http://localhost:2222/rest/annotate'
CONF = .4
SUPP = 20


def annotate(in_dir):
    req_time_total = 0
    req_num = 0
    annot_usable_total = 0
    annot_doc_num = 0
    for fn in os.listdir(in_dir):
        if os.path.splitext(fn)[-1] != '.txt':
            continue
        path = os.path.join(in_dir, fn)
        with open(path) as f:
            txt = f.read()
        t1 = time.time()
        try:
            annotations = spotlight.annotate(ANNOT_URL, txt, CONF, SUPP)
        except spotlight.SpotlightException:
            print('spotlight fail')
            continue
        except requests.exceptions.RequestException:
            print('requests fail')
            continue
        t2 = time.time()
        req_num += 1
        req_time_total += t2 - t1

        annot_doc_num += 1
        annot_usable_total += len(annotations)

        base_name = os.path.splitext(fn)[0]
        new_fn = '{}_annot.json'.format(base_name)
        new_path = os.path.join(in_dir, new_fn)
        annots_minimal = [[a['offset'],
                           a['offset']+len(a['surfaceForm']),
                           a['URI'].replace('http://dbpedia.org/resource/', '')
                           ] for a in annotations]
        with open(new_path, 'w') as f:
            f.write(json.dumps(annots_minimal))
        # print('- - - {}/? - - - -'.format(annot_doc_num))
        # print('avg query time: {}s'.format(req_time_total/req_num))
        # print('avg usable annot.: {}'.format(annot_usable_total/annot_doc_num))
        # for an in annotations:
        #     word = an['surfaceForm']
        #     suffix = txt[an['offset']+len(word):][:10]
        #     suffix_clean = suffix.strip()[:7]
        #     if '{{cite:' == suffix_clean:
        #         print('{}\n{}'.format(word, suffix))
        #         input()


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('usage: python3 spotlight_annotate.py </path/to/in_dir>')
        sys.exit()
    in_dir = sys.argv[1]
    annotate(in_dir)
