""" Count sentences of a parsed and matched arXiv dump

    run 1:
        done
        # sentences: 238569766
    run 2 (remove citations to avoid confusion):
        done
        # sentences: 238546105
"""

import json
import os
import re
import sys
import string
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from db_model import Base, Bibitem, BibitemArxivIDMap
from nltk.tokenize.punkt import PunktSentenceTokenizer, PunktParameters

CITE_PATT = re.compile((r'\{\{cite:([0-9A-F]{8}-[0-9A-F]{4}-4[0-9A-F]{3}'
                         '-[89AB][0-9A-F]{3}-[0-9A-F]{12})\}\}'), re.I)
RE_WHITESPACE = re.compile(r'[\s]+', re.UNICODE)
RE_PUNCT = re.compile('[%s]' % re.escape(string.punctuation), re.UNICODE)
# ↑ modified from gensim.parsing.preprocessing.RE_PUNCT
RE_WORD = re.compile('[^\s%s]+' % re.escape(string.punctuation), re.UNICODE)

punkt_param = PunktParameters()
abbreviation = ['al', 'fig', 'e.g', 'i.e', 'eq', 'cf', 'ref', 'refs']
punkt_param.abbrev_types = set(abbreviation)
tokenizer = PunktSentenceTokenizer(punkt_param)


def generate(in_dir, db_uri=None):
    """ Count sentences

        If no db_uri is given, a SQLite file metadata.db is expected in in_dir.
    """

    if not db_uri:
        db_path = os.path.join(in_dir, 'metadata.db')
        db_uri = 'sqlite:///{}'.format(os.path.abspath(db_path))
    engine = create_engine(db_uri)

    print('querying DB')
    q = ('select distinct in_doc from bibitem')
    tuples = engine.execute(q).fetchall()
    num_sentences = 0
    tuple_idx = 0
    while tuple_idx < len(tuples):
        if tuple_idx % 1000 == 0:
            print('{}/{}'.format(tuple_idx, len(tuples)))
            print('# sentences: {}'.format(num_sentences))
        in_doc = tuples[tuple_idx][0]
        fn_txt = '{}.txt'.format(in_doc)
        path_txt = os.path.join(in_dir, fn_txt)
        if not os.path.isfile(path_txt):
            tuple_idx += 1
            continue
        with open(path_txt) as f:
            text = f.read()
        text = re.sub(CITE_PATT, ' CIT ', text)
        for sent_idx, sent_edx in tokenizer.span_tokenize(text):
            num_sentences += 1
        tuple_idx += 1
    print('done')
    print('# sentences: {}'.format(num_sentences))


if __name__ == '__main__':
    if len(sys.argv) not in [2, 3]:
        print(('usage: python3 ____.py </path/to/in/dir> [<db_uri>'
               ']'))
        sys.exit()
    in_dir = sys.argv[1]
    if len(sys.argv) == 3:
        db_uri = sys.argv[2]
        ret = generate(in_dir, db_uri=db_uri)
    else:
        ret = generate(in_dir)
    if not ret:
        sys.exit()
