import chardet
import gzip
import magic
import os
import re
import shutil
import subprocess
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


def log(msg):
    with open(os.path.join(OUT_DIR, 'log.txt'), 'a') as f:
        f.write('{}\n'.format(msg))


def read_file(path):
    try:
        with open(path) as f:
            cntnt = f.read()
    except UnicodeDecodeError:
        blob = open(path, 'rb').read()
        m = magic.Magic(mime_encoding=True)
        encoding = m.from_buffer(blob)
        try:
            cntnt = blob.decode(encoding)
        except (UnicodeDecodeError, LookupError) as e:
            encoding = chardet.detect(blob)['encoding']
            cntnt = blob.decode(encoding, errors='replace')
    return cntnt

def read_gzipped_file(path):
    blob = gzip.open(path, 'rb').read()
    m = magic.Magic(mime_encoding=True)
    encoding = m.from_buffer(blob)
    try:
        cntnt = blob.decode(encoding)
    except (UnicodeDecodeError, LookupError) as e:
        encoding = chardet.detect(blob)['encoding']
        cntnt = blob.decode(encoding, errors='replace')
    return cntnt


if not os.path.isdir(IN_DIR):
    log('invalid dump directory')

if not os.path.isdir(OUT_DIR):
    os.makedirs(OUT_DIR)

for fn in os.listdir(IN_DIR):
    path = os.path.join(IN_DIR, fn)
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
                    cntnt = read_file(tmp_file_path)
                    if MAIN_TEX_SIGN in cntnt:
                        main_tex_path = tmp_file_path
                if main_tex_path is None:
                    log(('couldn\'t find main tex file in dump archive {}'
                         '').format(fn))
                    continue
                # identify bbl file if present
                bbl_path = None
                for rfn in rfnames:
                    if os.path.splitext(rfn)[1] not in ['.bbl', '.bib']:
                        continue
                    tmp_file_path = os.path.join(tmp_dir_path, rfn)
                    cntnt = read_file(tmp_file_path)
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
                # flatten to single tex file and save
                new_tex_fn = '{}.tex'.format(aid)
                tmp_dest = os.path.join(tmp_dir_path, new_tex_fn)
                out = open(tmp_dest, mode='w')
                err = open(os.path.join(OUT_DIR, 'log_latexpand.txt'), 'a')
                err.write('------------- {} -------------'.format(aid))
                err.flush()
                subprocess.run(latexpand_args, stdout=out, stderr=err)
                out.close()
                err.close()
                # re-read and write to ensure utf-8 b/c latexpand doesn't
                # behave
                cntnt = read_file(tmp_dest)
                dest = os.path.join(OUT_DIR, new_tex_fn)
                with open(dest, mode='w', encoding='utf-8') as f:
                    f.write(cntnt)
        else:
            # extraxt gzipped tex file
            cntnt = read_gzipped_file(path)
            if not MAIN_TEX_SIGN in cntnt:
                log('unexpected content in dump archive {}'.format(fn))
                continue
            new_fn = '{}.tex'.format(aid)
            dest = os.path.join(OUT_DIR, new_fn)
            with open(dest, mode='w', encoding='utf-8') as f:
                f.write(cntnt)
    else:
        log('unexpected file {} in dump directory'.format(fn))
