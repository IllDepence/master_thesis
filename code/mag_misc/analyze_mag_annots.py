""" Analyze MAG FoS annotations in citation contexts
"""

import json
import os
import re
import sys
import string
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from db_model import Base, Bibitem, BibitemArxivIDMap, BibitemMAGIDMap

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


def generate(in_dir, db_uri=None, context_size=100, min_contexts=1,
             with_placeholder=True, global_ids='mag'):
    """ Generate a list of citation contexts, given criteria:
            context_size (in words)
            min_contexts
            with_placeholder

        If no db_uri is given, a SQLite file metadata.db is expected in in_dir.
    """

    with open('field_of_study/FieldsOfStudy.txt') as f:
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

    if not db_uri:
        db_path = os.path.join(in_dir, 'metadata.db')
        db_uri = 'sqlite:///{}'.format(os.path.abspath(db_path))
    engine = create_engine(db_uri)
    Base.metadata.create_all(engine)
    Base.metadata.bind = engine
    DBSession = sessionmaker(bind=engine)
    session = DBSession()

    print('querying DB')
    if global_ids == 'mag':
        have_global_id = session.query(BibitemMAGIDMap.mag_id).\
                            subquery()
        bibitems = session.query(Bibitem, BibitemMAGIDMap).\
                    filter(Bibitem.uuid == BibitemMAGIDMap.uuid).\
                    filter(BibitemMAGIDMap.mag_id.in_(have_global_id)).\
                    all()
    else:
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
        if global_ids == 'mag':
            aid = bibitem.BibitemMAGIDMap.mag_id
        else:
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
    # rands = [2553, 3962, 4338, 10912, 11885, 12470, 17478, 20545, 25184, 26708, 27623, 27831, 28887, 29230, 33179, 33297, 35111, 36293, 39451, 41346]
    # ridx = 0
    num_fos_total = 0
    num_fos_max = -1
    num_fos_0 = 0
    num_fos_1 = 0
    num_fos_2 = 0
    num_fos_3 = 0
    num_fos_4 = 0
    num_fos_gt4 = 0
    num_fos_min = 9999999
    num_contexts = 0
    num_level = [0, 0, 0, 0, 0, 0]
    for aid, doc_list in cited_docs.items():
        tmp_list = []
        num_docs = 0
        for doc in doc_list:
            in_doc = doc['in_doc']
            fn_txt = '{}.txt'.format(in_doc)
            text_file = os.path.join(in_dir, fn_txt)
            with open(text_file) as f:
                text = f.read()
            fn_annot = '{}_fos.ann'.format(in_doc)
            annot_file = os.path.join(in_dir, fn_annot)
            if os.path.isfile(annot_file):
                with open(annot_file) as f:
                    ann_lines = f.readlines()
                    annots = []
                    for ann_line in ann_lines:
                        fos, disp, start, end, mid, conf = ann_line.split('\t')
                        # annots.append((fos, disp, start, end, mid, conf))
                        if float(conf) > 5:
                            annots.append((fos, disp, start, end, mid, conf))
            else:
                continue
            marker = '{{{{cite:{}}}}}'.format(doc['uuid'])
            marker_found = False
            for m in re.finditer(marker, text):
                num_contexts += 1
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
                # debug_annots = []
                for annot in annots:
                    start = int(annot[2])
                    end = int(annot[3])
                    dbp_id = annot[4].split('/')[-1]
                    if start <= max_start and end >= min_end:
                        context_annot.append(dbp_id)
                        if dbp_id in fos_id_tup_map:
                            fos_tup = fos_id_tup_map[dbp_id]
                            level = fos_tup[4]
                            num_level[level] += 1
                        # debug_annots.append([annot[0]-min_end, annot[1]-min_end, annot[2]])
                num_fos_total += len(context_annot)
                if len(context_annot) > num_fos_max:
                    num_fos_max = len(context_annot)
                if len(context_annot) < num_fos_min:
                    num_fos_min = len(context_annot)
                if len(context_annot) == 0:
                    num_fos_0 += 1
                elif len(context_annot) == 1:
                    num_fos_1 += 1
                elif len(context_annot) == 2:
                    num_fos_2 += 1
                elif len(context_annot) == 3:
                    num_fos_3 += 1
                elif len(context_annot) == 4:
                    num_fos_4 += 1
                else:
                    num_fos_gt4 += 1

                if num_contexts%1000 == 0:
                    print('avg. annot./context: {}'.format(
                        num_fos_total/num_contexts
                        ))
                    print('min. annot./context: {}'.format(num_fos_min))
                    print('max. annot./context: {}'.format(num_fos_max))
                    print('0: {} ({})'.format(num_fos_0, num_fos_0/num_contexts))
                    print('1: {} ({})'.format(num_fos_1, num_fos_1/num_contexts))
                    print('2: {} ({})'.format(num_fos_2, num_fos_2/num_contexts))
                    print('3: {} ({})'.format(num_fos_3, num_fos_3/num_contexts))
                    print('4: {} ({})'.format(num_fos_4, num_fos_4/num_contexts))
                    print('>4: {} ({})'.format(num_fos_gt4, num_fos_gt4/num_contexts))
                    for level in range(6):
                        print('total #ann. @level {}: {}'.format(
                            level, num_level[level]))

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
    # sys.exit()
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
