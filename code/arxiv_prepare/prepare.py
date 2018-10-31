import os
import shutil
import sys
import tarfile
import tempfile
from normalize_arxiv_dump import normalize
from parse_latex_tralics import parse
from match_bibitems import match


def prepare(in_dir, out_dir_dir, db_uri=None):
    if not os.path.isdir(in_dir):
        print('input directory does not exist')
        return False

    ext_sample = os.path.splitext((os.listdir(in_dir)[0]))[-1]
    # heuristic to tell apart single uncompressed "sub dump" from a folder of
    # many still compressed dumps
    if ext_sample in ['.gz', '.pdf']:
        in_folder_name = os.path.normpath(in_dir).split(os.sep)[-1]
    elif ext_sample in ['.tar']:
        # create dir for *all* .gz files, extract, move
        in_folder_name = 'all'
        out_dir_gz = os.path.join(out_dir_dir,
                                  '{}_flattened'.format(in_folder_name))
        os.makedirs(out_dir_gz)
        for tar_fn in os.listdir(in_dir):
            tar_path = os.path.join(in_dir, tar_fn)
            try:
                is_tar = tarfile.is_tarfile(tar_path)
            except IsADirectoryError:
                print(('unexpected folder in "{}" in {}. skipping'
                       '').format(tar_fn, in_dir))
                continue
            if is_tar:
                with tempfile.TemporaryDirectory() as tmp_dir_path:
                    tar = tarfile.open(tar_path)
                    tar.extractall(path=tmp_dir_path)
                    containing_folder = os.listdir(tmp_dir_path)[0]
                    containing_path = os.path.join(tmp_dir_path,
                                                   containing_folder)
                    for gz_fn in os.listdir(containing_path):
                        gz_path_tmp = os.path.join(containing_path, gz_fn)
                        gz_path_new = os.path.join(out_dir_gz, gz_fn)
                        shutil.move(gz_path_tmp, gz_path_new)
        # adjust in_dir
        in_dir = out_dir_gz
    else:
        print('don\'t understand input directory')
        return False

    out_dir_norm = os.path.join(out_dir_dir,
                                '{}_normalized'.format(in_folder_name))
    out_dir_text = os.path.join(out_dir_dir,
                                '{}_text'.format(in_folder_name))
    for out_dir in [out_dir_dir, out_dir_norm, out_dir_text]:
        if not os.path.isdir(out_dir):
            os.makedirs(out_dir)
    normalize(in_dir, out_dir_norm)
    if db_uri:
        parse(out_dir_norm, out_dir_text, INCREMENTAL=True, db_uri=db_uri)
        match(db_uri=db_uri)
    else:
        parse(out_dir_norm, out_dir_text, INCREMENTAL=True)
        match(in_dir=out_dir_text)


if __name__ == '__main__':
    if len(sys.argv) not in [3, 4]:
        print(('usage: python3 prepare.py </path/to/in/dir> </path/to/out/dir>'
               ' [<db_uri>]'))
        sys.exit()
    in_dir = sys.argv[1]
    out_dir_dir = sys.argv[2]
    if len(sys.argv) == 4:
        db_uri = sys.argv[3]
        ret = prepare(in_dir, out_dir_dir, db_uri=db_uri)
    else:
        ret = prepare(in_dir, out_dir_dir)
    if not ret:
        sys.exit()
