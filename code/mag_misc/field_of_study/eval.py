import json
import operator
import os
import subprocess
import tempfile

items = []
with open('items_mag_fos_test.csv') as f:
    item_lines = f.readlines()
    for item_line in item_lines:
        parts = item_line.split(',')
        items.append((parts[0], parts[3]))

with open('mag_fos_map_tops.json') as f:
    fos_map = json.load(f)

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

def annotate(text):
    """ Not used b/c of long startup time.
    """

    with tempfile.TemporaryDirectory() as in_path:
        with tempfile.TemporaryDirectory() as out_path:
            with open(os.path.join(in_path, 'tmp'), 'w') as f:
                f.write(text)
            linking_args = ['java',
                            '-jar',
                            ('/home/saiert/mag_linking_copy/'
                             'linking_file_tarek.jar'),
                            in_path,
                            out_path]
            try:
                subprocess.run(linking_args,
                               cwd='/home/saiert/mag_linking_copy')
            except subprocess.TimeoutExpired as e:
                print('FAILED: {}.'.format(e))
                return False
            with open(os.path.join(out_path, 'tmp')) as f:
                annot_lines = f.readlines()
            annots = [l.split('\t')[4].split('/')[-1] for l in annot_lines]
            return annots

num_correct = 0
for idx, item in enumerate(items):
    mid = item[0]
    context = item[1]
    truth = [t[0] for t in fos_map[mid]]
    # with open('citcontxs/{}_{}'.format(mid, idx), 'w') as f:
    #     f.write(context)
    # continue
    print('#{}_{}:\ntruth: {}'.format(mid, idx, ', '.join([id_name_map[i] for i in truth])))
    # print(context)
    # annots = annotate(context)
    with open('citcontxs_out/{}_{}'.format(mid, idx)) as f:
        annot_lines = f.readlines()
    annots = [l.split('\t')[4].split('/')[-1] for l in annot_lines]
    tops = {}
    for annot in annots:
        a_tops = top_foss(annot)
        for at in a_tops:
            if at not in tops:
                tops[at] = 0
            tops[at] += 1
    sorted_tops = sorted(tops.items(),
                         key=operator.itemgetter(1),
                         reverse=True)
    if len(sorted_tops) == 0:
        print('no annotations')
        continue
    top_score = sorted_tops[0][1]
    foss_guess = []
    for st in sorted_tops:
        if st[1] == top_score:
            foss_guess.append(st[0])
        else:
            break
    print('guess: {}'.format(', '.join([id_name_map[i] for i in foss_guess])))
    truth_set = set(truth)
    guess_set = set(foss_guess)
    overlap = truth_set.intersection(guess_set)
    if len(overlap) > 0:
        num_correct += 1
print('> {:.3f} <'.format(num_correct/len(items)))
