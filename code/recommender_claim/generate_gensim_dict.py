""" Generate a Gensim dictionary.

    19401145 lines → 105 GB memory
"""

import os
import sys
from gensim import corpora, models
from util import bow_preprocess_string
from six import iteritems


def build(docs_path):
    """ - foo
    """

    texts = []  # for dictionary generation
    total = sum(1 for line in open(docs_path))
    with open(docs_path) as f:
        for idx, line in enumerate(f):
            if idx%10000 == 0:
                print('{}/{} lines'.format(idx, total))
            try:
                aid, adjacent, in_doc, text = line.split('\u241E')
            except ValueError:
                aid, adjacent, in_doc, text, fos_annot = line.split('\u241E')
            preprocessed_text = bow_preprocess_string(text)
            texts.append(preprocessed_text)
    print('building dictionary')
    dictionary = corpora.Dictionary(texts)
    once_ids = [tokenid for tokenid, docfreq in iteritems(dictionary.dfs)
                if docfreq == 1]
    dictionary.filter_tokens(once_ids)
    dictionary.compactify()
    print('saving dictionary')
    docs_fn = os.path.split(docs_path)[-1]
    docs_n = os.path.splitext(docs_path)[0]
    dictionary.save('{}.dict'.format(docs_n))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('usage: python3 generate_gensim_dict.py </path/to/docs_file>')
        sys.exit()
    docs_path = sys.argv[1]
    build(docs_path)
