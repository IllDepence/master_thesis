import operator
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

annot_file = sys.argv[1]
with open(annot_file) as f:
    annot_lines = f.readlines()

foss = {}
for l in annot_lines:
    parts = l.split('\t')
    mid = parts[4].split('/')[-1].strip()
    if mid not in id_name_map:
        continue
    print(id_name_map[mid])
    for t in top_foss(mid):
        if t not in foss:
            foss[t] = 0
        foss[t] += 1

print('- - - - - - - - ')
sorted_foss = sorted(foss.items(), key=operator.itemgetter(1), reverse=True)
for tup in sorted_foss:
    print('{}: {}'.format(tup[1], id_name_map[tup[0]]))
