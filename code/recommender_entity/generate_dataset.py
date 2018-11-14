""" Generate datasets from a parsed and matched arXiv dump
"""

import json
import os
import re
import sys
import string
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from db_model import Base, Bibitem, BibitemArxivIDMap

CITE_PATT = re.compile((r'\{\{cite:([0-9A-F]{8}-[0-9A-F]{4}-4[0-9A-F]{3}'
                         '-[89AB][0-9A-F]{3}-[0-9A-F]{12})\}\}'), re.I)
RE_WHITESPACE = re.compile(r'[\s]+', re.UNICODE)
RE_PUNCT = re.compile('[%s]' % re.escape(string.punctuation), re.UNICODE)
# ↑ modified from gensim.parsing.preprocessing.RE_PUNCT
RE_WORD = re.compile('[^\s%s]+' % re.escape(string.punctuation), re.UNICODE)


def clean_window_distance_words(adfix, num_words, backwards=False):
    """ In the given direction, calculate how many characters you have to pass
        to include <num_words> words (not counting citations as words).

        Example:
          adfix:     ", {{cite:foo}} this is an example {{cite:bar}}. Baz bam."
          num_words: 5
          backwards: false

        -> 51
    """

    words = 0
    win_dist = 0
    if backwards:
        while words < num_words:
            pos = (len(adfix) - win_dist)
            char = adfix[pos-1:pos]
            if char == '}':
                if CITE_PATT.match(adfix[pos-45:pos]):
                    # jump citation
                    win_dist += 45
                    continue
                else:
                    win_dist += 1
                    continue
            elif RE_PUNCT.match(char):
                win_dist += 1
                continue
            elif RE_WHITESPACE.match(char):
                win_dist += 1
                continue
            elif RE_WORD.match(char):
                # count and jump word
                word_len = 0
                word_char = char
                while RE_WORD.match(word_char):
                    shift = word_len + 1
                    word_char = adfix[pos-1-shift:pos-shift]
                    word_len += 1
                win_dist += word_len
                words += 1
            elif char == '':
                break
            else:
                print('something went wrong in clean_window_distance_words')
    else:
        while words < num_words:
            char = adfix[win_dist:win_dist+1]
            if char == '{':
                if CITE_PATT.match(adfix[win_dist:win_dist+45]):
                    # jump citation
                    win_dist += 45
                    continue
                else:
                    win_dist += 1
                    continue
            elif RE_PUNCT.match(char):
                win_dist += 1
                continue
            elif RE_WHITESPACE.match(char):
                win_dist += 1
                continue
            elif RE_WORD.match(char):
                # count and jump word
                jump = RE_WORD.search(adfix[win_dist:]).end()
                win_dist += max(jump, 1)
                words += 1
            elif char == '':
                break
            else:
                print('something went wrong in clean_window_distance_words')
    return win_dist

def find_adjacent_citations(adfix, uuid_aid_map, backwards=False):
    """ Given text after or before a citation, find all directly adjacent
        citations.
    """

    if backwards:
        perimeter = adfix[-50:]
    else:
        perimeter = adfix[:50]
    match = CITE_PATT.search(perimeter)
    if not match:
        return []
    uuid = match.group(1)
    if uuid not in uuid_aid_map:
        return []
    aid = uuid_aid_map[uuid]
    margin = perimeter.index(match.group(0))
    if backwards:
        adfix = adfix[:-(50-margin)]
    else:
        adfix = adfix[45+margin:]
    moar = find_adjacent_citations(adfix, uuid_aid_map, backwards=backwards)
    return [aid] + moar


def generate(in_dir, db_uri=None, context_size=100, min_contexts=4,
             with_placeholder=True):
    """ Generate a list of citation contexts, given criteria:
            context_size (in words)
            min_contexts
            with_placeholder

        If no db_uri is given, a SQLite file metadata.db is expected in in_dir.
    """

    if not db_uri:
        db_path = os.path.join(in_dir, 'metadata.db')
        db_uri = 'sqlite:///{}'.format(os.path.abspath(db_path))
    engine = create_engine(db_uri)
    Base.metadata.create_all(engine)
    Base.metadata.bind = engine
    DBSession = sessionmaker(bind=engine)
    session = DBSession()

    print('querying DB')
    have_global_id = session.query(BibitemArxivIDMap.arxiv_id).\
                        subquery()
    bibitems = session.query(Bibitem, BibitemArxivIDMap).\
                filter(Bibitem.uuid == BibitemArxivIDMap.uuid).\
                filter(BibitemArxivIDMap.arxiv_id.in_(have_global_id)).\
                all()
    print('merging bibitems')
    cited_docs_pre = {}
    uuid_aid_map = {}
    for bibitem in bibitems:
        aid = bibitem.BibitemArxivIDMap.arxiv_id
        uuid = bibitem.Bibitem.uuid
        uuid_aid_map[uuid] = aid
        in_doc = bibitem.Bibitem.in_doc
        if aid not in cited_docs_pre:
            cited_docs_pre[aid] = {}
        if in_doc not in cited_docs_pre[aid]:
            cited_docs_pre[aid][in_doc] = []
        cited_docs_pre[aid][in_doc].append(uuid)
    print('checking merging results')
    cited_docs = {}
    for aid, doc_dict in cited_docs_pre.items():
        # for evaluation we *need* at least 2 documents containing citation
        # contexts (in order to perform a per doc test/train split)
        if len(doc_dict) > 1:
            cited_docs[aid] = []
            for in_doc, uuid_list in doc_dict.items():
                cited_docs[aid].append({
                    'uuid': uuid_list[0],  # uuid_list should always be len. 1
                    'in_doc': in_doc
                    })
    print('going through docs')
    contexts = []
    for aid, doc_list in cited_docs.items():
        tmp_list = []
        num_docs = 0
        for doc in doc_list:
            in_doc = doc['in_doc']
            fn_txt = '{}.txt'.format(in_doc)
            text_file = os.path.join(in_dir, fn_txt)
            with open(text_file) as f:
                text = f.read()
            fn_annot = '{}_annot.json'.format(in_doc)
            annot_file = os.path.join(in_dir, fn_annot)
            if os.path.isfile(annot_file):
                with open(annot_file) as f:
                    annots = json.load(f)
            else:
                annots = []
            marker = '{{{{cite:{}}}}}'.format(doc['uuid'])
            marker_found = False
            for m in re.finditer(marker, text):
                margin = int(context_size/2)
                idx = m.start()
                edx = m.end()
                pre = text[:idx]
                post = text[edx:]
                adj_pre = find_adjacent_citations(pre, uuid_aid_map,
                                                  backwards=True)
                adj_post = find_adjacent_citations(post, uuid_aid_map)
                adjacent_citations = adj_pre + adj_post

                win_pre = clean_window_distance_words(pre, margin,
                                                      backwards=True)
                win_post = clean_window_distance_words(post, margin)

                pre = pre[-win_pre:]
                post = post[:win_post]

                # determine contained annotations
                min_end = idx-win_pre
                max_start = edx+win_post
                context_annot = []
                for annot in annots:
                    start = annot[0]
                    end = annot[1]
                    dbp_id = annot[2]
                    if start <= max_start and end >= min_end:
                        context_annot.append(dbp_id)

                placeholder = ''
                if with_placeholder:
                    placeholder = ' MAINCIT '
                context = '{}{}{}'.format(pre, placeholder, post)

                context = re.sub(CITE_PATT, ' CIT ', context)
                context = re.sub(r'[\r\n]+', ' ', context)
                context = re.sub(RE_WHITESPACE, ' ', context)

                adj_cit_str = '{}'.format('\u241F'.join(adjacent_citations))
                annot_str = '{}'.format('\u241F'.join(context_annot))
                tmp_list.append([aid, adj_cit_str, in_doc, context,
                                 annot_str])
                marker_found = True
            if marker_found:
                num_docs += 1
        if len(tmp_list) >= min_contexts and num_docs > 1:
            contexts.extend(tmp_list)
    print(len(contexts))
    with open('items.csv', 'w') as f:
        for vals in contexts:
            line = '{}\n'.format('\u241E'.join(vals))
            f.write(line)

if __name__ == '__main__':
    if len(sys.argv) not in [2, 3]:
        print(('usage: python3 generate_dataset.py </path/to/in/dir> [<db_uri>'
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
