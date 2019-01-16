""" Generate a Gensim dictionary.

    19401145 lines → 105 GB memory
"""

import os
import sys
from gensim import corpora, models


def build(docs_path):
    """ - foo
    """

    texts = []  # for dictionary generation
    total = sum(1 for line in open(docs_path))
    with open(docs_path) as f:
        for idx, line in enumerate(f):
            if idx%10000 == 0:
                print('{}/{} lines'.format(idx, total))
            aid, adjacent, in_doc, text = line.split('\u241E')
            # fill texts
            texts.append(text.split())
    print('building dictionary')
    dictionary = corpora.Dictionary(texts)
    print('saving dictionary')
    dictionary.save('3s5min5min.dict')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('usage: python3 _____.py </path/to/docs_file>')
        sys.exit()
    docs_path = sys.argv[1]
    build(docs_path)
