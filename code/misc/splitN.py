""" Split contents of a directory in N.

    Creates folders i0, i1, ..., iN  (where files will be moved)
                and o0, o1, ..., oN  (will be left empty)
"""

import math
import os
import shutil
import sys

in_dir = sys.argv[1]
N = int(sys.argv[2])
fns = os.listdir(in_dir)
batch_size = math.floor(len(fns)/N)
out_folder_names = []
print('folder: {}'.format(in_dir))
print('splits: {}'.format(N))
print('batch size: {}'.format(batch_size))
print('ok?')
input()
for i in range(N):
    out_folder_names.append('i{}'.format(i))
    os.mkdir(os.path.join(in_dir, 'i{}'.format(i)))
for i in range(N):
    os.mkdir(os.path.join(in_dir, 'o{}'.format(i)))

for idx, fn in enumerate(fns):
    path = os.path.join(in_dir, fn)
    out_folder_idx = min(int(idx/batch_size), (N-1))
    path_new = os.path.join(in_dir, out_folder_names[out_folder_idx], fn)
    shutil.move(path, path_new)
