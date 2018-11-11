import os
import requests
import sys
import time
from lxml import etree

ANNOT_URL = 'http://132.230.150.127:8080/text-annotation-with-offset-Nov14/'


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
        req = '<item><text>{}</text></item>'.format(txt)
        t1 = time.time()
        try:
            res = requests.post(ANNOT_URL, data=req.encode('utf-8'))
        except requests.exceptions.RequestException:
            print('request fail')
            continue
        t2 = time.time()
        req_num += 1
        req_time_total += t2 - t1

        if res.status_code != 200:
            print('status code {} fail'.format(res.status_code))
            continue

        try:
            tree = etree.fromstring(res.text.encode('utf-8'))
        except etree.XMLSyntaxError:
            print('XML fail')
            continue
        num_usable = 0
        for ann in tree.xpath('//annotation'):
            if float(ann.get('weight')) < 0.1:
                continue
            num_usable += 1
            # wiki_link = ann.xpath('.//description[@lang="en"]')[0].get('URL')
            # for men in ann.xpath('.//mention'):
            #     print(men.get('words'))
            # print('→ {}'.format(wiki_link))
        annot_doc_num += 1
        annot_usable_total += num_usable
        print('- - - {}/? - - - -'.format(annot_doc_num))
        print('avg query time: {}s'.format(req_time_total/req_num))
        print('avg usable annot.: {}'.format(annot_usable_total/annot_doc_num))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('usage: python3 nel_annotate.py </path/to/in_dir>')
        sys.exit()
    in_dir = sys.argv[1]
    annotate(in_dir)
