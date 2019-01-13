""" Split contents of a directory in 10.

    Creates folders i0, i1, ..., i9  (where files will be moved)
                and o0, o1, ..., o9  (will be left empty)
"""

import math
import os
import shutil
import sys

in_dir = sys.argv[1]
fns = os.listdir(in_dir)
batch_size = math.floor(len(fns)/10)
out_folder_names = []
for i in range(10):
    out_folder_names.append('i{}'.format(i))
    os.mkdir(os.path.join(in_dir, 'i{}'.format(i)))
for i in range(10):
    os.mkdir(os.path.join(in_dir, 'o{}'.format(i)))

for idx, fn in enumerate(fns):
    path = os.path.join(in_dir, fn)
    out_folder_idx = min(int(idx/batch_size), 9)
    path_new = os.path.join(in_dir, out_folder_names[out_folder_idx], fn)
    shutil.move(path, path_new)
