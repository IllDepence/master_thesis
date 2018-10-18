""" Normalize a arXiv dump

    - copy PDF files as is
    - unzip gzipped single files
        - copy if it's a LaTeX file
    - extract gzipped tar archives
        - try to flatten contents to a single LaTeX file
        - ignores non LaTeX contents (HTML, PS, TeX, ...)
"""

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
MAIN_TEX_PATT = re.compile(r'(\\begin\s*\{\s*document\s*\})', re.I)
# ^ with capturing parentheses so that the pattern can be used for splitting
PDF_EXT_PATT = re.compile(r'^\.pdf$', re.I)
GZ_EXT_PATT = re.compile(r'^\.gz$', re.I)
TEX_EXT_PATT = re.compile(r'^\.tex$', re.I)
NON_TEXT_PATT = re.compile(r'^\.(pdf|eps|jpg|png|gif)$', re.I)
BBL_SIGN = '\\bibitem'
# agressive math pre-removal
PRE_FILTER_MATH = False
FILTER_PATTS = []
for env in ['equation', 'displaymath', 'array', 'eqnarray', 'align', 'gather',
            'multline', 'flalign', 'alignat']:
    s = r'\\begin\{{{0}[*]?\}}.+?\\end\{{{0}\}}'.format(env)
    patt = re.compile(s, re.I | re.M | re.S)
    FILTER_PATTS.append(patt)
FILTER_PATTS.append(re.compile(r'\$\$.+?\$\$', re.S))
FILTER_PATTS.append(re.compile(r'\$.+?\$', re.S))
FILTER_PATTS.append(re.compile(r'\\\(.+?\\\)', re.S))
FILTER_PATTS.append(re.compile(r'\\\[.+?\\\]', re.S))


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


def remove_math(latex_str):
    parts = re.split(MAIN_TEX_PATT, latex_str, maxsplit=1)
    for patt in FILTER_PATTS:
         parts[2] = re.sub(patt, '', parts[2])
    return ''.join(parts)


if not os.path.isdir(IN_DIR):
    print('dump directory does not exist')
    sys.exit()

if not os.path.isdir(OUT_DIR):
    os.makedirs(OUT_DIR)

for fn in os.listdir(IN_DIR):
    path = os.path.join(IN_DIR, fn)
    aid, ext = os.path.splitext(fn)
    if PDF_EXT_PATT.match(ext):
        # copy over pdf file as is
        dest = os.path.join(OUT_DIR, fn)
        shutil.copyfile(path, dest)
    elif GZ_EXT_PATT.match(ext):
        if tarfile.is_tarfile(path):
            with tempfile.TemporaryDirectory() as tmp_dir_path:
                # extract archive contents
                tar = tarfile.open(path)
                fnames = tar.getnames()
                tar.extractall(path=tmp_dir_path)
                # identify main tex file
                main_tex_path = None
                ignored_names = []
                # check .tex files first
                for tfn in fnames:
                    if not TEX_EXT_PATT.match(os.path.splitext(tfn)[1]):
                        ignored_names.append(tfn)
                        continue
                    tmp_file_path = os.path.join(tmp_dir_path, tfn)
                    cntnt = read_file(tmp_file_path)
                    if re.search(MAIN_TEX_PATT, cntnt) is not None:
                        main_tex_path = tmp_file_path
                # try other files
                if main_tex_path is None:
                    for tfn in ignored_names:
                        tmp_file_path = os.path.join(tmp_dir_path, tfn)
                        if NON_TEXT_PATT.match(os.path.splitext(tfn)[1]):
                            continue
                        try:
                            cntnt = read_file(tmp_file_path)
                            if re.search(MAIN_TEX_PATT, cntnt) is not None:
                                main_tex_path = tmp_file_path
                        except:
                            continue
                # give up
                if main_tex_path is None:
                    log(('couldn\'t find main tex file in dump archive {}'
                         '').format(fn))
                    continue
                # identify bbl file if present
                bbl_path = None
                for tfn in fnames:
                    tmp_file_path = os.path.join(tmp_dir_path, tfn)
                    if NON_TEXT_PATT.match(os.path.splitext(tfn)[1]):
                        continue
                    try:
                        cntnt = read_file(tmp_file_path)
                        if re.search(MAIN_TEX_PATT, cntnt) is not None:
                            continue
                        if BBL_SIGN in cntnt:
                            bbl_path = tmp_file_path
                    except:
                        continue
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
                err.write('\n------------- {} -------------\n'.format(aid))
                err.flush()
                subprocess.run(latexpand_args, stdout=out, stderr=err,
                               cwd=tmp_dir_path)
                out.close()
                err.close()
                # re-read and write to ensure utf-8 b/c latexpand doesn't
                # behave
                cntnt = read_file(tmp_dest)
                if PRE_FILTER_MATH:
                    cntnt = remove_math(cntnt)
                dest = os.path.join(OUT_DIR, new_tex_fn)
                with open(dest, mode='w', encoding='utf-8') as f:
                    f.write(cntnt)
        else:
            # extraxt gzipped tex file
            cntnt = read_gzipped_file(path)
            if re.search(MAIN_TEX_PATT, cntnt) is None:
                log('unexpected content in dump archive {}'.format(fn))
                continue
            new_fn = '{}.tex'.format(aid)
            if PRE_FILTER_MATH:
                cntnt = remove_math(cntnt)
            dest = os.path.join(OUT_DIR, new_fn)
            with open(dest, mode='w', encoding='utf-8') as f:
                f.write(cntnt)
    else:
        log('unexpected file {} in dump directory'.format(fn))