import gzip
import json
import os
import sys
import tarfile


def id_from_tar_member(member):
    """ 1701/1701.05327.gz -> 1701.05327
    """

    fn = os.path.split(member.name)[-1]
    aid = os.path.splitext(fn)[0]
    return aid


def sample(dump_dir, sample_dir, sample_file):
    if not (os.path.isdir(dump_dir) and os.path.isfile(sample_file)):
        print('Either dump_dir or sample_file doesn\'t exist.')
        return False
    if not os.path.isdir(sample_dir):
        os.makedirs(sample_dir)
    archive_fns = os.listdir(dump_dir)
    with open(sample_file) as f:
        sample_map = json.load(f)
    # for each month
    sample_fns = []
    for month, id_list in sample_map.items():
        sample_fns.extend([i.replace('/', '') for i in id_list])
    for month, id_list in sample_map.items():
        print(month)
        archive_prefix = 'arXiv_src_{}'.format(month)
        month_fns = [afn for afn in archive_fns if archive_prefix in afn]
        # for each dump archive in that month
        for archive_fn in month_fns:
            tar = tarfile.open(os.path.join(dump_dir, archive_fn))
            # extract all that are part of the sample
            sample_members = []
            for member in tar.getmembers():
                if id_from_tar_member(member) not in sample_fns:
                    continue
                member.name = os.path.basename(member.name)
                sample_members.append(member)
            tar.extractall(path=sample_dir, members=sample_members)

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print(('usage: python3 sample.py </path/to/dump/dir> </path/to/sample/'
               'dir> <path/to/sample/file>'))
        sys.exit()
    dump_dir = sys.argv[1]
    sample_dir = sys.argv[2]
    sample_file = sys.argv[3]
    ret = sample(dump_dir, sample_dir, sample_file)
    if not ret:
        sys.exit()
