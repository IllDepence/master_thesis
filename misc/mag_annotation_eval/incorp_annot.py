import os
import sys

for fn in os.listdir(os.getcwd()):
    name, ext = os.path.splitext(fn)
    ann_fn = '{}.ann'.format(name)
    inc_fn = '{}_inc.txt'.format(name)
    if ext != '.txt':
        continue
    print(name)
    with open(fn) as f:
        txt = f.read()
    with open(ann_fn) as f:
        ann_lines = f.readlines()
    ann_tups = []
    for ann_line in ann_lines:
        fos, disp, start, end, mid, conf = ann_line.split('\t')
        ann_tups.append((fos, disp, start, end, mid, conf))
    ann_tups.sort(key=lambda x: int(x[2]))
    shift = 0
    for ann_tup in ann_tups:
        fos = ann_tup[0]
        disp = ann_tup[1]
        start = int(ann_tup[2])
        end = int(ann_tup[3])
        if start < 0:
            continue
        start = int(start) + shift
        end = int(end) + shift
        pre = txt[:start]
        post = txt[end:]
        insert = '[{}]({})'.format(disp, fos)

        # print('{}-{}'.format(start, end))
        # print(txt[max(0, start-25):max(0, end+25)])

        shift += len(insert) - len(disp)
        txt = pre + insert + post
        # print(txt[max(0, start-25):max(0, end+25+shift)])
        # input()
    with open(inc_fn, 'w') as f:
         f.write(txt)
