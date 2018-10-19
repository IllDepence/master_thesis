""" convert latex files to plain text with nice citation markers

    TODO:
        - mby get rid of tables (and figures)?
        - mby remove commas between citations?
        - remove non textbody leftovers somehow?
"""

import os
import re
import subprocess
import sys
import tempfile
import uuid
from lxml import etree
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_model import Base, Bibitem, BibitemLinkMap, BibitemArxivIDMap

PDF_EXT_PATT = re.compile(r'^\.pdf$', re.I)
ARXIV_URL_PATT = re.compile((r'arxiv\.org\/[a-z0-9]{1,10}\/(([a-z0-9-]{1,15}\/'
                              ')?[\d\.]{5,10}(v\d)?$)'), re.I)


def parse(IN_DIR, OUT_DIR, INCREMENTAL, db_uri=None):
    def log(msg):
        with open(os.path.join(OUT_DIR, 'log.txt'), 'a') as f:
            f.write('{}\n'.format(msg))

    if not os.path.isdir(IN_DIR):
        print('input directory does not exist')
        return False

    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)

    if not db_uri:
        db_path = os.path.join(OUT_DIR, 'metadata.db')
        db_uri = 'sqlite:///{}'.format(os.path.abspath(db_path))
    engine = create_engine(db_uri)
    Base.metadata.create_all(engine)
    Base.metadata.bind = engine
    DBSession = sessionmaker(bind=engine)
    session = DBSession()

    for fn in os.listdir(IN_DIR):
        path = os.path.join(IN_DIR, fn)
        aid, ext = os.path.splitext(fn)
        out_txt_path = os.path.join(OUT_DIR, '{}.txt'.format(aid))
        if INCREMENTAL and os.path.isfile(out_txt_path):
            # print('{} already in output directory, skipping'.format(aid))
            continue
        # print(aid)
        if PDF_EXT_PATT.match(ext):
            log('skipping file {} (PDF)'.format(fn))
            continue

        with tempfile.TemporaryDirectory() as tmp_dir_path:
            tmp_xml_path = os.path.join(tmp_dir_path, '{}.xml'.format(aid))
            # run latexml
            tralics_args = ['tralics',
                            '-silent',
                            '-noxmlerror',
                            '-utf8',
                            '-oe8',
                            '-entnames=false',
                            '-nomathml',
                            '-output_dir={}'.format(tmp_dir_path),
                            path]

            out = open(os.path.join(OUT_DIR, 'log_tralics.txt'), 'a')
            err = open(os.path.join(tmp_dir_path, 'tralics_out.txt'), mode='w')
            out.write('\n------------- {} -------------\n'.format(aid))
            out.flush()
            try:
                subprocess.run(tralics_args, stdout=out, stderr=err, timeout=5)
            except subprocess.TimeoutExpired as e:
                print('FAILED {}. skipping'.format(aid))
                log('\n--- {} ---\n{}\n----------\n'.format(aid, e))
                continue
            out.close()
            err.close()

            # get mathless plain text from latexml output
            parser = etree.XMLParser()
            if not os.path.isfile(tmp_xml_path):
                print('FAILED {}. skipping'.format(aid))
                log(('\n--- {} ---\n{}\n----------\n'
                     '').format(aid, 'no tralics output'))
                continue
            with open(tmp_xml_path) as f:
                try:
                    tree = etree.parse(f, parser)
                except etree.XMLSyntaxError as e:
                    print('FAILED {}. skipping'.format(aid))
                    log('\n--- {} ---\n{}\n----------\n'.format(aid, e))
                    continue
            etree.strip_elements(tree, 'formula', with_tail=False)

            # processing of citation markers
            bibitems = tree.xpath('//bibitem')
            bibkey_map = {}

            for bi in bibitems:
                uid = str(uuid.uuid4())
                local_key = bi.get('id')
                bibkey_map[local_key] = uid
                containing_p = bi.getparent()
                text = etree.tostring(containing_p,
                                      encoding='unicode',
                                      method='text')
                text = re.sub('\s+', ' ', text).strip()
                bibitem_db = Bibitem(uuid=uid, in_doc=aid, bibitem_string=text)
                session.add(bibitem_db)
                session.flush()
                for xref in containing_p.findall('xref'):
                    link = xref.get('url')
                    match = ARXIV_URL_PATT.search(link)
                    if match:
                        id_part = match.group(1)
                        aid_db = BibitemArxivIDMap(uuid=uid, arxiv_id=id_part)
                        session.add(aid_db)
                        session.flush()
                    link_db = BibitemLinkMap(uuid=uid, link=link)
                    session.add(link_db)
                    session.flush()

            citations = tree.xpath('//cit')
            for cit in citations:
                elem = cit.find('ref')
                if elem is None:
                    log(('WARNING: cite element in {} contains no ref element'
                         '').format(aid))
                    continue
                ref = elem.get('target')
                replace_text = ''
                if ref in bibkey_map:
                    marker = '{{{{cite:{}}}}}'.format(bibkey_map[ref])
                    replace_text += marker
                else:
                    log(('WARNING: unmatched bibliography key {} for doc {}'
                         '').format(ref, aid))
                if cit.tail:
                    cit.tail = replace_text + cit.tail
                else:
                    cit.tail = replace_text
            # /processing of citation markers
            etree.strip_elements(tree, 'Bibliography', with_tail=False)
            etree.strip_elements(tree, 'bibitem', with_tail=False)
            etree.strip_elements(tree, 'cit', with_tail=False)
            etree.strip_tags(tree, '*')
            tree_str = etree.tostring(tree, encoding='unicode', method='text')
            # tree_str = re.sub('\s+', ' ', tree_str).strip()

            with open(out_txt_path, 'w') as f:
                f.write(tree_str)
            session.commit()
    return True


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(('usage: python3 parse_latex_tralics.py </path/to/in/dir> </path'
               '/to/out/dir>'))
        sys.exit()
    IN_DIR = sys.argv[1]
    OUT_DIR = sys.argv[2]
    ret = parse(IN_DIR, OUT_DIR, INCREMENTAL=True)
    if not ret:
        sys.exit()
