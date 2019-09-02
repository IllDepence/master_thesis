""" Extract contexts from the unarXive data set.
"""

import argparse
import json
import os
import re
import sys
import string
from sqlalchemy import create_engine
from nltk import tokenize

CITE_PATT = re.compile((r'\{\{cite:([0-9A-F]{8}-[0-9A-F]{4}-4[0-9A-F]{3}'
                         '-[89AB][0-9A-F]{3}-[0-9A-F]{12})\}\}'), re.I)
RE_WHITESPACE = re.compile(r'[\s]+', re.UNICODE)
RE_PUNCT = re.compile('[%s]' % re.escape(string.punctuation), re.UNICODE)
# ↑ modified from gensim.parsing.preprocessing.RE_PUNCT
RE_WORD = re.compile('[^\s%s]+' % re.escape(string.punctuation), re.UNICODE)

tokenizer = tokenize.load('tokenizers/punkt/english.pickle')
abbreviation = ['al', 'fig', 'e.g', 'i.e', 'eq', 'cf', 'ref', 'refs']
for abbr in abbreviation:
    tokenizer._params.abbrev_types.add(abbr)


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


def find_adjacent_citations(adfix, uuid_ctd_mid_map, backwards=False):
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
    if uuid not in uuid_ctd_mid_map:
        return []
    id_tuple = uuid_ctd_mid_map[uuid]
    margin = perimeter.index(match.group(0))
    if backwards:
        adfix = adfix[:-(50-margin)]
    else:
        adfix = adfix[45+margin:]
    moar = find_adjacent_citations(adfix, uuid_ctd_mid_map, backwards=backwards)
    return [id_tuple] + moar


def context_sentences(pre, post, num_sent_pre, num_sent_post):
    """ Return context w/ specified number of sentences before and after the
        citing sentence.
    """

    cit_marker = 'MAINCIT'
    text = '{} {} {}'.format(pre, cit_marker, post)

    sentences_pre = []
    citing_sentence = None
    sentences_post = []
    passed_middle = False

    for sentence in tokenizer.tokenize(text):
        if not passed_middle and cit_marker in sentence:
            citing_sentence = sentence
            passed_middle = True
            continue
        if not passed_middle:
            sentences_pre.append(sentence)
        else:
            sentences_post.append(sentence)
            if len(sentences_post) >= num_sent_post:
                break

    if num_sent_pre > 0:
        pre_s = sentences_pre[-num_sent_pre:]
    else:
        pre_s = []
    if num_sent_post >= 0:
        post_s = sentences_post[:num_sent_post]
    else:
        post_s = []
    sentences = pre_s + [citing_sentence] + post_s

    return ' '.join(sentences)


def generate(in_dir, db_uri, context_margin_unit, context_margin_pre,
             context_margin_post, min_contexts, min_citing_docs,
             sample_size, output_file):
    """ Generate a list of citation contexts, given criteria:
            context_margin_unit (s=setences, w=words)
            context_margin_pre
            context_margin_post
            min_contexts
            min_citing_docs
            sample_size (number of cited documents)

        If no db_uri is given, a SQLite file refs.db is expected in in_dir.
    """

    if not db_uri:
        db_path = os.path.join(in_dir, 'refs.db')
        db_uri = 'sqlite:///{}'.format(os.path.abspath(db_path))
    engine = create_engine(db_uri)

    print('querying DB')
    limit_insert = ''
    if sample_size > 0:
        print('limiting to a sample of {} cited docs'.format(sample_size))
        limit_insert = ' limit :lim' # order by random()
    q = ('select uuid, cited_mag_id, cited_arxiv_id, citing_mag_id, citing_arxiv_id'
         ' from bibitem'
         ' where cited_mag_id in '
         '(select cited_mag_id from bibitem group by cited_mag_id '
           'having count(uuid) > {}{})'
         ' order by cited_mag_id').format(min_citing_docs-1, limit_insert);
    if sample_size > 0:
        tuples = engine.execute(q, sample_size).fetchall()
    else:
        tuples = engine.execute(q).fetchall()
    print('building uuid->cited_mag_id in memory map')
    uuid_ctd_mid_map = {}
    for uuid, ctd_mid, ctd_aid, ctg_mid, ctg_aid in tuples:
        uuid_ctd_mid_map[uuid] = [ctd_mid, ctd_aid]
    print('going through {} citing docs'.format(len(tuples)))
    contexts = []
    tuple_idx = 0
    ctd_mag_id = tuples[0][1]
    bag_mag_id = ctd_mag_id
    num_used_cited_docs = 0
    nums_contexts = []
    while tuple_idx < len(tuples):
        tmp_list = []
        num_docs = 0
        while ctd_mag_id == bag_mag_id and tuple_idx < len(tuples):
            if tuple_idx % 1000 == 0:
                print('{}/{}'.format(tuple_idx, len(tuples)))
            uuid = tuples[tuple_idx][0]
            ctd_aid = tuples[tuple_idx][2]
            ctg_mid = tuples[tuple_idx][3]
            ctg_aid = tuples[tuple_idx][4]
            fn_txt = '{}.txt'.format(ctg_aid)
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
                idx = m.start()
                edx = m.end()
                pre = text[:idx]
                post = text[edx:]
                adj_pre = find_adjacent_citations(pre, uuid_ctd_mid_map,
                                                  backwards=True)
                adj_post = find_adjacent_citations(post, uuid_ctd_mid_map)
                # NOTE: in case of a (small) sample, adjacent citations will
                #       almost always be empty. that's not a bug.
                adjacent_citations = adj_pre + adj_post

                if context_margin_unit == 's':
                    org_context = context_sentences(
                        pre, post, context_margin_pre, context_margin_post
                        )
                elif context_margin_unit == 'w':
                    win_pre = clean_window_distance_words(pre, context_margin_pre,
                                                          backwards=True)
                    win_post = clean_window_distance_words(post, context_margin_post)
                    pre = pre[-win_pre:]
                    post = post[:win_post]
                    org_context = '{} MAINCIT {}'.format(pre, post)
                else:
                    print('invalid context size unit')
                    return False

                context = re.sub(r'[\r\n]', ' ', org_context)
                context = re.sub(CITE_PATT, ' CIT ', context)
                context = re.sub(r'[\r\n]+', ' ', context)
                context = re.sub(RE_WHITESPACE, ' ', context)

                adjacent_citations_mids = [str(t[0]) for t in adjacent_citations]
                adjacent_citations_aids = [str(t[1]) for t in adjacent_citations]
                adj_mid_str = '{}'.format('\u241F'.join(adjacent_citations_mids))
                # leaves 'None' strings in CSV but preserves alignment w/ IDs of other
                # type (e.g. 3,7,9|None,hep5,None -> MAG 7 corresponds to arXiv hep5)
                adj_aid_str = '{}'.format('\u241F'.join(adjacent_citations_aids))
                vals = [ctd_mag_id, adj_mid_str, ctg_mid, ctd_aid, adj_aid_str, ctg_aid, context]
                vals = [str(v) for v in vals]
                tmp_list.append(vals)
                marker_found = True
            if marker_found:
                num_docs += 1
            tuple_idx += 1
            if tuple_idx < len(tuples):
                ctd_mag_id = tuples[tuple_idx][1]

        if tuple_idx < len(tuples):
            bag_mag_id = tuples[tuple_idx][1]
        if len(tmp_list) >= min_contexts and num_docs >= min_citing_docs:
            contexts.extend(tmp_list)
            num_used_cited_docs += 1
            nums_contexts.append(len(tmp_list))
    print('ended up using {} cited docs'.format(num_used_cited_docs))
    print('number of contexts (Σ: {}): {}'.format(
        sum(nums_contexts), nums_contexts)
        )
    print('writing contexts to file {}'.format(output_file))
    with open(output_file, 'w') as f:
        for vals in contexts:
            line = '{}\n'.format('\u241E'.join(vals))
            f.write(line)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=('Script for extracting '
        'citation contexts from the unarXive data set.'))
    parser.add_argument(
        'in_dir',
        help='path of the directory in which the plain text files are stored')
    parser.add_argument(
        '-b',
        '--db_uri',
        dest='db_uri',
        default=None,
        help='database URI (defaults to sqlite:///<in_dir>/refs.db)')
    parser.add_argument(
        '-f',
        '--output_file',
        dest='output_file',
        default='items.csv',
        help='name of output file (defaults to items.csv)')
    parser.add_argument(
        '-u',
        '--context_margin_unit',
        dest='margin_unit',
        choices=('s', 'w'),
        default='s',
        help=('context margin unit (possible values: \'s\'=sentences, '
              '\'w\'=words; defaults to \'s\')'))
    parser.add_argument(
        '-e',
        '--context_margin_pre',
        dest='margin_pre',
        type=int,
        default=1,
        help=('number of <context_margin_unit> before the citing sentence '
              '(defaults to 1)'))
    parser.add_argument(
        '-o',
        '--context_margin_post',
        dest='margin_post',
        type=int,
        default=1,
        help=('number of <context_margin_unit> after the citing sentence '
              '(defaults to 1)'))
    parser.add_argument(
        '-c',
        '--min_contexts',
        dest='min_contexts',
        type=int,
        default=1,
        help=('require <min_context> contexts per cited document (defaults to '
              '1)'))
    parser.add_argument(
        '-d',
        '--min_citing_docs',
        dest='min_citing_docs',
        type=int,
        default=1,
        help=('require <min_citing_docs> citing documents for a cited '
              'document (defaults to 1)'))
    parser.add_argument(
        '-s',
        '--sample_size',
        dest='sample_size',
        type=int,
        default=-1,
        help=('only use a sample of <sample_size> cited documents (all are '
              'used if argument is not given)'))

    args = parser.parse_args()
    ret = generate(args.in_dir, args.db_uri, args.margin_unit, args.margin_pre,
                   args.margin_post, args.min_contexts, args.min_citing_docs,
                   args.sample_size, args.output_file)
    if not ret:
        sys.exit()
