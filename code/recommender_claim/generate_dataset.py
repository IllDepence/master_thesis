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


def find_adjacent_citations(adfix, uuid_mid_map, backwards=False):
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
    if uuid not in uuid_mid_map:
        return []
    aid = uuid_mid_map[uuid]
    margin = perimeter.index(match.group(0))
    if backwards:
        adfix = adfix[:-(50-margin)]
    else:
        adfix = adfix[45+margin:]
    moar = find_adjacent_citations(adfix, uuid_mid_map, backwards=backwards)
    return [aid] + moar


def window_distance_sentences(prefix, postfix, num_sentences):
    """ Return the window distance that includes <num_sentences> sentences.

        (Go heuristically by periods and then check properly.)
    """

    directional_margin = int((num_sentences-1)/2)
    safety_multiplier = 3
    pre_end = False
    post_end = False
    window_found = False

    while not window_found and not (pre_end and post_end):
        dots_to_pass = (directional_margin + 1) * safety_multiplier
        pre = ''
        post = ''
        for backwards in [True, False]:
            if backwards:
                adfix = prefix
            else:
                adfix = postfix
            num_dots = 0
            win_dist = 0
            if backwards:
                start = len(adfix) - 1
                end = 0
                delta = -1
            else:
                start = 0
                end = len(adfix) - 1
                delta = 1
            pos = start
            while num_dots < dots_to_pass:
                if backwards and pos <= end:
                    break
                if not backwards and pos >= end:
                    break
                char = adfix[pos]
                if char == '.':
                    num_dots += 1
                win_dist += 1
                pos += delta

            if backwards and pos+delta <= end:
                pre_end = True
            if not backwards and pos+delta >= end:
                post_end = True

            if backwards:
                win_dist -= 1  # cut the dot
                pre = adfix[-win_dist:]
            else:
                post = adfix[:win_dist]
        cit_marker = 'TMP\u200CCIT'
        tmp_cut = '{}{}{}'.format(pre, cit_marker, post)

        sentences_pre = []
        sentence_mid = None
        sentences_post = []
        passed_middle = False
        for sent_idx, sent_edx in tokenizer.span_tokenize(tmp_cut):
            sentence = tmp_cut[sent_idx:sent_edx]
            if cit_marker in sentence:
                sentence_mid = sentence
                passed_middle = True
                continue
            if not passed_middle:
                dist_to_marker = len(pre) - sent_idx
                sentences_pre.append((sentence, dist_to_marker))
            else:
                dist_to_marker = sent_edx - (len(pre) + len(cit_marker))
                sentences_post.append((sentence, dist_to_marker))

        if len(sentences_pre) >= directional_margin and \
                len(sentences_post) >= directional_margin:
            window_found = True
        else:
            safety_multiplier *= 3

    m = re.search(cit_marker, sentence_mid)
    sentence_mid_pre_part_length = m.start()
    sentence_mid_post_part_length = len(sentence_mid) - m.end()
    if num_sentences == 1:
        sentences_pre_dist = 0
        sentences_post_dist = 0
    else:
        if len(sentences_pre) >= directional_margin:
            sentences_pre_dist = sentences_pre[-directional_margin][1] - \
                                                sentence_mid_pre_part_length
        else:
            sentences_pre_dist = len(prefix)
        if len(sentences_post) >= directional_margin:
            sentences_post_dist = sentences_post[directional_margin-1][1] - \
                                                sentence_mid_post_part_length
        else:
            sentences_post_dist = len(postfix)
    pre_dist = sentences_pre_dist + m.start()
    post_dist = sentences_post_dist + (len(sentence_mid) - m.end())
    return pre_dist, post_dist


def in_doc_to_aid(in_doc):
    aid = in_doc
    if re.search('[a-z]', in_doc, re.I):
        m = re.search('[a-z][0-9]', in_doc, re.I)
        cut = m.start() + 1
        aid = '{}/{}'.format(in_doc[:cut], in_doc[cut:])
    return aid


def get_cont_ann(idx, edx, win_pre, win_post, annots, fosp_map, threshold=5.0):
    """ Get all FoS annotations within the context
    """

    min_end = idx-win_pre
    max_start = edx+win_post
    context_annot = []
    context_annot_ext = []
    for annot in annots:
        start = int(annot[2])
        end = int(annot[3])
        fos_id = annot[4].split('/')[-1]
        conf = float(annot[5])
        if conf <= threshold:
            continue
        if start <= max_start and end >= min_end:
            context_annot.append(fos_id)
            ext = [fos_id]
            if fos_id in fosp_map:
                ext = ext + fosp_map[fos_id]
            context_annot_ext.extend(ext)
    return context_annot, context_annot_ext


def get_preceding_ann(idx, annots, fos_id_tup_map, conf_thr=5.0, level_thr=2):
    """ Get directly preceding FoS annotation.
    """

    prec_annot = None
    for annot in annots:
        start = int(annot[2])
        end = int(annot[3])
        fos_id = annot[4].split('/')[-1]
        conf = float(annot[5])
        fos_tup = fos_id_tup_map.get(fos_id)
        if fos_tup:
            level = fos_tup[4]
        else:
            level = -1
        if conf <= conf_thr:
            continue
        if level < level_thr:
            continue
        if idx-end <= 5 and idx-end > 0:
            prec_annot = fos_id
            break
    return prec_annot


def generate(in_dir, db_uri=None, context_size=1, context_size_unit='s',
             min_contexts=5, min_citing_docs=5, with_placeholder=True,
             sample_size=1000, restrict_fos_citing=False, fos_annot=True,
             only_directly_preceding_fos_annot=False):
    """ Generate a list of citation contexts, given criteria:
            context_size
            context_size_unit (s=setences, w=words)
            min_contexts
            min_citing_docs
            with_placeholder
            sample_size

        If no db_uri is given, a SQLite file metadata.db is expected in in_dir.
    """

    if not db_uri:
        db_path = os.path.join(in_dir, 'metadata.db')
        db_uri = 'sqlite:///{}'.format(os.path.abspath(db_path))
    engine = create_engine(db_uri)

    if restrict_fos_citing:
        aid_db_uri = 'sqlite:///aid_fos.db'
        aid_engine = create_engine(aid_db_uri, connect_args={'timeout': 60})
        print('generating aid FoS map')
        tpls = aid_engine.execute(
            'select aid, fos from paper'
            ).fetchall()
        aid_fos_map = {}
        for tpl in tpls:
            aid_fos_map[tpl[0]] = tpl[1]
    if fos_annot:
        # fos child->parent map
        fosp_path = 'FieldOfStudyChildren.txt'
        if not os.path.isfile(fosp_path):
            print('Couldn\'t find file FieldOfStudyChildren.txt.')
            sys.exit()
        print('generating FoS child->parent map')
        with open(fosp_path) as f:
            fosp_lines = f.readlines()

        fosp_map = {}
        for l in fosp_lines:
            fields = l.split('\t')
            parent = fields[0].strip()
            child = fields[1].strip()
            if child not in fosp_map:
                fosp_map[child] = []
            fosp_map[child].append(parent)
        # fos info
        fosi_path = 'FieldsOfStudy.txt'
        if not os.path.isfile(fosi_path):
            print('Couldn\'t find file FieldsOfStudy.txt.')
            sys.exit()
        with open(fosi_path) as f:
            fos_lines = f.readlines()
        fos_id_tup_map = {}
        for l in fos_lines:
            fields = l.split('\t')
            fid = fields[0].strip()
            rank = fields[1].strip()
            norm_name = fields[2].strip()
            disp_name = fields[3].strip()
            try:
                level = int(fields[5].strip())
            except ValueError:
                continue
            fos_id_tup_map[fid] = (fid, rank, norm_name, disp_name, level)

    # with open('/home/saiert/semantic_web_mag_ids') as f:
    #     sem_web_ids = [l.strip() for l in f.readlines()]
    # sem_web_where_in = '({})'.format(','.join(["'{}'".format(i) for i in sem_web_ids]))

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
           'having count(uuid) > {}{})'
         ' order by mag_id').format(min_citing_docs-1, limit_insert);
    if sample_size > 0:
        tuples = engine.execute(q, sample_size).fetchall()
    else:
        tuples = engine.execute(q).fetchall()
    print('building uuid->mag_id in memory map')
    uuid_mid_map = {}
    for uuid, mag_id, in_doc in tuples:
        uuid_mid_map[uuid] = mag_id
    print('going through {} citing docs'.format(len(tuples)))
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
            if tuple_idx % 1000 == 0:
                print('{}/{}'.format(tuple_idx, len(tuples)))
            uuid = tuples[tuple_idx][0]
            in_doc = tuples[tuple_idx][2]
            if restrict_fos_citing:
                aid = in_doc_to_aid(in_doc)
                citing_fos = aid_fos_map.get(aid, False)
                if citing_fos != restrict_fos_citing:
                    tuple_idx += 1
                    continue
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

            if fos_annot:
                annots = []
                txt_dir_path = os.path.split(path_txt)[0]
                path_parts = os.path.split(txt_dir_path)
                annot_dir_path = os.path.join(
                    path_parts[0],
                    '{}_fos-annot'.format(path_parts[1])
                    )
                annot_file = os.path.join(annot_dir_path, fn_txt)
                if os.path.isfile(annot_file):
                    with open(annot_file) as f:
                        ann_lines = f.readlines()
                        annots = []
                        for ann_line in ann_lines:
                            fos_ann, disp, start, end, mid, conf = ann_line.split('\t')
                            annots.append((fos_ann, disp, start, end, mid, conf))

            marker = '{{{{cite:{}}}}}'.format(uuid)
            marker_found = False
            for m in re.finditer(marker, text):
                idx = m.start()
                edx = m.end()
                pre = text[:idx]
                post = text[edx:]
                adj_pre = find_adjacent_citations(pre, uuid_mid_map,
                                                  backwards=True)
                adj_post = find_adjacent_citations(post, uuid_mid_map)
                # NOTE: in case of a (small) sample, adjacent citations will
                #       almost always be empty. that's not a bug.
                adjacent_citations = adj_pre + adj_post

                if context_size_unit == 's':
                    win_pre, win_post = window_distance_sentences(
                        pre, post, context_size
                        )
                elif context_size_unit == 'w':
                    win_pre = clean_window_distance_words(pre, 50)
                    win_post = clean_window_distance_words(post, 50,
                                                           backwards=False)
                else:
                    print('invalid context size unit')
                    return False

                pre = pre[-win_pre:]
                post = post[:win_post]

                if fos_annot:
                    context_annot, context_annot_ext = get_cont_ann(
                        idx, edx, win_pre, win_post, annots, fosp_map)
                    if only_directly_preceding_fos_annot:
                        prec_annot = get_preceding_ann(
                            idx, annots, fos_id_tup_map)
                        context_annot = []
                        if prec_annot:
                            context_annot = [prec_annot]
                    cont_ann_str = '{}'.format(
                        '\u241F'.join(context_annot))  # TODO: try 2 steps ext

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
                if fos_annot:
                    tmp_list.append([mag_id, adj_cit_str, in_doc, context,
                        cont_ann_str])
                else:
                    tmp_list.append([mag_id, adj_cit_str, in_doc, context])
                marker_found = True
            if marker_found:
                num_docs += 1
            tuple_idx += 1
            if tuple_idx < len(tuples):
                mag_id = tuples[tuple_idx][1]

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
    with open('items_1ksample_wFoS_1s_5mindoc_5mincont.csv', 'w') as f:  # TODO: PHYS
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
