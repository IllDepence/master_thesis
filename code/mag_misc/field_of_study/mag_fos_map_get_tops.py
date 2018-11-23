import operator
import json
import sys

with open('FieldOfStudyChildren.txt') as f:
    fosc_lines = f.readlines()
with open('FieldsOfStudy.txt') as f:
    fos_lines = f.readlines()

fosc_map = {}
for l in fosc_lines:
    fields = l.split('\t')
    parent = fields[0].strip()
    child = fields[1].strip()
    if child not in fosc_map:
        fosc_map[child] = []
    fosc_map[child].append(parent)

id_name_map = {}
for l in fos_lines:
    fields = l.split('\t')
    fid = fields[0].strip()
    disp_name = fields[3].strip()
    id_name_map[fid] = disp_name

def top_foss(child):
    if child not in fosc_map:
        return [child]
    else:
        ret = []
        for parent in fosc_map[child]:
            ret.extend(top_foss(parent))
        return list(set(ret))  # prevent duplicates

with open('mag_fos_map.json') as f:
    paper_map = json.load(f)

paper_map_e = {}
for mid, foss in paper_map.items():
    top_f_all = {}
    for fos in foss:
        top_f = top_foss(fos)
        for t in top_f:
            if t not in top_f_all:
                top_f_all[t] = 0
            top_f_all[t] += 1
    sorted_tpfl = sorted(top_f_all.items(),
                         key=operator.itemgetter(1),
                         reverse=True)
    paper_map_e[mid] = sorted_tpfl

with open('mag_fos_map_tops.json', 'w') as f:
    f.write(json.dumps(paper_map_e))
