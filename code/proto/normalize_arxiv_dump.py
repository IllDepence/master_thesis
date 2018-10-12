import gzip
import os
import re
import shutil
import sys
import tarfile
import tempfile

if len(sys.argv) != 3:
    print(('usage: python3 nomalize_arxiv_dump.py </path/to/dump/dir> </path/t'
           'o/out/dir>'))
    sys.exit()

IN_DIR = sys.argv[1]
OUT_DIR = sys.argv[2]
MAIN_TEX_SIGN = '\\begin{document}'
BBL_SIGN = '\\bibitem'

if not os.path.isdir(IN_DIR):
    print('invalid dump directory')

if not os.path.isdir(OUT_DIR):
    os.makedirs(OUT_DIR)

for path in os.listdir(IN_DIR):
    fn = os.path.basename(path)
    aid, ext = os.path.splitext(fn)
    if ext == '.pdf':
        # copy over pdf file as is
        dest = os.path.join(OUT_DIR, fn)
        shutil.copyfile(path, dest)
    elif ext == '.gz':
        if tarfile.is_tarfile(path):
            with tempfile.TemporaryDirectory() as tmp_dir_path:
                # extract archive contents
                tar = tarfile.open(path)
                files = tar.getmembers()
                rel_ext = ['.tex', '.bbl', '.bib', '.pdf']
                rel_files = [f for f in files if
                             os.path.splitext(f.name)[1] in rel_ext]
                rfnames = [f.name for f in rel_files if
                           os.path.splitext(f.name)[1]]
                tar.extractall(path=tmp_dir_path, members=rel_files)
                # identify main tex file
                main_tex_path = None
                for rfn in rfnames:
                    if os.path.splitext(rfn)[1] != '.tex':
                        continue
                    tmp_file_path = os.path.join(tmp_dir_path, rfn)
                    cntnt = ''
                    with open(tmp_file_path) as f:
                        cntnt = f.read()
                    if MAIN_TEX_SIGN in cntnt:
                        main_tex_path = tmp_file_path
                if main_tex_path is None:
                    print(('couldn\'t find main tex file in dump archive {}'
                           '').format(fn))
                    continue
                # identify bbl file if present
                bbl_path = None
                for rfn in rfnames:
                    if os.path.splitext(rfn)[1] not in ['.bbl', '.bib']:
                        continue
                    tmp_file_path = os.path.join(tmp_dir_path, rfn)
                    cntnt = ''
                    with open(tmp_file_path) as f:
                        cntnt = f.read()
                    if BBL_SIGN in cntnt:
                        bbl_path = tmp_file_path
                if bbl_path is None:
                    latexpand_args = ['latexpand',
                                      main_tex_path]
                else:
                    latexpand_args = ['latexpand',
                                      '--expand-bbl',
                                      bbl_path,
                                      main_tex_path]
                new_tex_fn = '{}.tex'.format(aid)
                dest = os.path.join(OUT_DIR, new_tex_fn)
                out = open(dest, 'w')
                subprocess.run(latexpand_args, stdout=out)
                out.close()
        else:
            # extraxt gzipped tex file
            cntnt = ''
            with gzip.open(path, 'rt') as f:
                cntnt = f.read()
            if not MAIN_TEX_SIGN in cntnt:
                print('unexpected content in dump archive {}'.format(fn))
                continue
            new_fn = '{}.tex'.format(aid)
            dest = os.path.join(OUT_DIR, new_fn)
            with open(dest, 'w') as f:
                f.write(cntnt)
    else:
        print('unexpected file {} in dump directory'.format(fn))
