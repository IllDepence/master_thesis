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


def generate(in_dir, db_uri=None, context_size=3, min_contexts=4,
             with_placeholder=True, sample_size=5):
    """ Generate a list of citation contexts, given criteria:
            context_size (in sentences)
            min_contexts
            with_placeholder
            sample_size

        If no db_uri is given, a SQLite file metadata.db is expected in in_dir.
    """

    if not db_uri:
        db_path = os.path.join(in_dir, 'metadata.db')
        db_uri = 'sqlite:///{}'.format(os.path.abspath(db_path))
    engine = create_engine(db_uri)
    # Base.metadata.create_all(engine)
    # Base.metadata.bind = engine
    # DBSession = sessionmaker(bind=engine)
    # session = DBSession()

    print('querying DB')
    limit_insert = ''
    if sample_size > 0:
        print('limiting to a sample of {} cited docs'.format(sample_size))
        limit_insert = ' order by random() limit :lim'
    q = ('select bibitem.uuid, mag_id, in_doc'
         ' from bibitemmagidmap join bibitem'
         ' on bibitemmagidmap.uuid = bibitem.uuid'
         ' where mag_id in '
         '(select mag_id from bibitemmagidmap group by mag_id '
           'having count(uuid) > 1{})'
         ' order by mag_id').format(limit_insert);
    if sample_size > 0:
        tuples = engine.execute(q, sample_size).fetchall()
    else:
        tuples = engine.execute(q).fetchall()
    print('building uuid->mag_id in memory map')
    uuid_aid_map = {}
    for uuid, mag_id, in_doc in tuples:
        uuid_aid_map[uuid] = mag_id
    print('going through {} docs'.format(len(tuples)))
    contexts = []
    tuple_idx = 0
    mag_id = tuples[0][1]
    bag_mag_id = mag_id
    num_used_cited_docs = 0
    nums_contexts = []
    while tuple_idx < len(tuples):
        tmp_list = []
        num_docs = 0
        while mag_id == bag_mag_id and tuple_idx < len(tuples):
            uuid = tuples[tuple_idx][0]
            mag_id = tuples[tuple_idx][1]
            in_doc = tuples[tuple_idx][2]
            fn_txt = '{}.txt'.format(in_doc)
            path_txt = os.path.join(in_dir, fn_txt)
            if not os.path.isfile(path_txt):
                # this is the case when a LaTeX source's \bibitems could be
                # parsed but the \cites couldn't (so the plaintext was removed
                # from the dataset)
                # TODO: clean DB of such cases
                tuple_idx += 1
                continue
            with open(path_txt) as f:
                text = f.read()
            marker = '{{{{cite:{}}}}}'.format(uuid)
            marker_found = False
            for m in re.finditer(marker, text):
                margin = int((context_size-1)/2)
                idx = m.start()
                edx = m.end()
                pre = text[:idx]
                post = text[edx:]
                adj_pre = find_adjacent_citations(pre, uuid_aid_map,
                                                  backwards=True)
                adj_post = find_adjacent_citations(post, uuid_aid_map)
                adjacent_citations = adj_pre + adj_post

                # TODO: jump <margin>*3 dots, split in sentences,
                #       if not enoug, jump more etc.
                #       then use sentence size citation context
                win_pre = clean_window_distance_words(pre, margin,
                                                    backwards=True)
                win_post = clean_window_distance_words(post, margin)

                pre = pre[-win_pre:]
                post = post[:win_post]

                placeholder = ''
                if with_placeholder:
                    placeholder = ' MAINCIT '
                context = '{}{}{}'.format(pre, placeholder, post)

                org_context = context
                org_context = re.sub(r'[\r\n]', ' ', org_context)
                context = re.sub(CITE_PATT, ' CIT ', context)
                context = re.sub(r'[\r\n]+', ' ', context)
                context = re.sub(RE_WHITESPACE, ' ', context)

                adj_cit_str = '{}'.format('\u241F'.join(adjacent_citations))
                tmp_list.append([mag_id, adj_cit_str, in_doc, context])
                marker_found = True
            if marker_found:
                num_docs += 1
            tuple_idx += 1

        if tuple_idx < len(tuples):
            bag_mag_id = tuples[tuple_idx][1]
        if len(tmp_list) >= min_contexts and num_docs > 1:
            contexts.extend(tmp_list)
            num_used_cited_docs += 1
            nums_contexts.append(len(tmp_list))
    print('ended up using {} cited docs'.format(num_used_cited_docs))
    print('number of contexts: {}'.format(nums_contexts))
    sys.exit()
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
