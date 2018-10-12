import gzip
import os
import re
import shutil
import sys
import tarfile

if len(sys.argv) != 3:
    print(('usage: python3 nomalize_arxiv_dump.py </path/to/dump/dir> </path/t'
           'o/out/dir>'))
    sys.exit()

IN_DIR = sys.argv[1]
OUT_DIR = sys.argv[2]

if not os.path.isdir(IN_DIR):
    print('invalid dump directory')

if not os.path.isdir(OUT_DIR):
    os.makedirs(OUT_DIR)

for path in os.listdir(IN_DIR):
    fn = os.path.basename(path)
    aid, ext = os.path.splitext(fn)
    if ext == 'pdf':
        # copy over pdf file as is
        dest = os.path.join(OUT_DIR, fn)
        shutil.copyfile(path, dest)
    elif ext == 'gz':
        if tarfile.is_tarfile(path):
            # extract tar archive
            # TODO
            # - determine main tex file
            # - flatten
            # - move
        else:
            # extraxt gzipped tex file
            with gzip.open(path, 'rt') as f:
                cntnt = f.read()
            if not '\\begin{document}' in cntnt:
                print('unexpected content in dump archive {}'.format(fn))
            new_fn = '{}.tex'.format(aid)
            dest = os.path.join(OUT_DIR, new_fn)
            with open(dest, 'w') as f:
                f.write(cntnt)
    else:
        print('unexpected file {} in dump directory'.format(fn))
