""" If CSV vals are
        cited_id, adj, citing_id, context[, pp, np]
    make them
        cited_id, adj, citing_id, context, fos[, pp, np]
    to have a consitent format with the arXiv CSV.
"""

import os
import sys


def build(docs_path):
    """ - foo
    """

    total = sum(1 for line in open(docs_path))
    orig_n = os.path.splitext(docs_path)[0]
    ext_path = '{}_phantomFoS_rename_me.csv'.format(orig_n)
    with open(docs_path) as fi:
        with open(ext_path, 'w') as fo:
            for idx, line in enumerate(fi):
                if idx%10000 == 0:
                    print('{}/{} lines'.format(idx, total))
                line = line.strip()
                vals = line.split('\u241E')
                new_vals = vals[:4] + [''] + vals[4:]
                ext_line = '{}\n'.format('\u241E'.join(new_vals))
                fo.write(ext_line)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('usage: python3 _.py </path/to/docs_file>')
        sys.exit()
    docs_path = sys.argv[1]
    build(docs_path)
