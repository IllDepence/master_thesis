import os
import sys
import tarfile
from normalize_arxiv_dump import normalize
from parse_latex_tralics import parse
from match_bibitems import match


def prepare_silgle(in_dir, out_dir_dir, db_uri=None):
    in_folder_name = os.path.normpath(in_dir).split(os.sep)[-1]
    out_dir_norm = os.path.join(out_dir_dir,
                                '{}_normalized'.format(in_folder_name))
    out_dir_text = os.path.join(out_dir_dir,
                                '{}_text'.format(in_folder_name))
    for out_dir in [out_dir_dir, out_dir_norm, out_dir_text]:
        if not os.path.isdir(out_dir):
            os.makedirs(out_dir)
    normalize(in_dir, out_dir_norm)
    if db_uri:
        parse(out_dir_norm, out_dir_text, INCREMENTAL=True)
        match(in_dir=in_dir)
    else:
        parse(out_dir_norm, out_dir_text, INCREMENTAL=True, db_uri=db_uri)
        match(db_uri=db_uri)


def prepare(in_dir, out_dir_dir, db_uri=None):
    if not os.path.isdir(in_dir):
        print('input directory does not exist')
        return False
    ext_sample = os.path.splitext((os.listdir(in_dir)[0]))[-1]
    # heristic to tell apart single uncompressed "sub dump" from a folder of
    # many still compressed dumps
    if ext_sample in ['.gz', '.pdf']:
        prepare_silgle(in_dir, out_dir_dir, db_uri)
    elif ext_sample in ['.tar']:
        for fn in os.listdir(in_dir):
            if tarfile.is_tarfile(in_dir):
                tar = tarfile.open(fn)
                tar.extractall(path=tmp_dir_path)  # TODO: hier weiter
    else:
        print('don\'t understand input directory')
        return False


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
