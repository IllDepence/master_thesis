""" Get FoS as given in MAG for CSV export of contexts/makerk patts/...
"""

import sys
import json
import operator
from sqlalchemy import create_engine

aid2mid = {}
with open('mag_id_2_arxiv_id.csv') as f:
    for line in f:
        mid, sourcetype, aurl, aid = line.strip().split(',')
        aid2mid[aid] = int(mid)

# ua_db_uri = 'sqlite:////home/saiert/arxiv_v2.1.1_refs.db'
# ua_engine = create_engine(ua_db_uri)  #, connect_args={'timeout': 60}

m_db_uri = 'postgresql+psycopg2://mag:1maG$@localhost:5432/MAG19'
m_engine = create_engine(m_db_uri)  #,
#    connect_args={'options': '-c statement_timeout=60000'}
#    )

qm = 'SELECT fieldofstudyid, displayname, level FROM fieldsofstudy'
fostups = m_engine.execute(qm).fetchall()
fos_name_map = {}
lvl0fos_ids = []
for ft in fostups:
    fos_name_map[ft[0]] = ft[1]
    if ft[2] == 0:
        lvl0fos_ids.append(ft[0])

cited_fos_count_map = {}
cited_fos_count_map_basic = {}
citing_fos_count_map = {}
citing_fos_count_map_basic = {}
both_fos_count_map = {}
both_fos_count_map_basic = {}

with open('context_patts_specific_part_in_cited.csv') as f:
    for i, line in enumerate(f):
        if i%10000 == 0:
            print(i)
        vals = line.strip().split('\u241E')
        cited_mid = vals[0]
        # cited
        qm = ('SELECT fieldofstudyid FROM paperfieldsofstudy'
              ' WHERE paperid = \'{}\''
              ).format(cited_mid)
        fosids_d = m_engine.execute(qm).fetchall()
        for fi in [t[0] for t in fosids_d]:
            fos_name = fos_name_map[fi]
            if fos_name not in cited_fos_count_map:
                cited_fos_count_map[fos_name] = 0
            cited_fos_count_map[fos_name] += 1
            if fi in lvl0fos_ids:
                if fos_name not in cited_fos_count_map_basic:
                    cited_fos_count_map_basic[fos_name] = 0
                cited_fos_count_map_basic[fos_name] += 1
        citing_aid = vals[2]
        citing_mid = aid2mid.get(citing_aid, False)
        if citing_mid:
            # citing
            qm = ('SELECT fieldofstudyid FROM paperfieldsofstudy'
                  ' WHERE paperid = \'{}\''
                  ).format(citing_mid)
            fosids_g = m_engine.execute(qm).fetchall()
            for fi in [t[0] for t in fosids_g]:
                fos_name = fos_name_map[fi]
                if fos_name not in citing_fos_count_map:
                    citing_fos_count_map[fos_name] = 0
                citing_fos_count_map[fos_name] += 1
                if fi in lvl0fos_ids:
                    if fos_name not in citing_fos_count_map_basic:
                        citing_fos_count_map_basic[fos_name] = 0
                    citing_fos_count_map_basic[fos_name] += 1
            # both (citing-cited)
            for fid in [t[0] for t in fosids_d]:
                for fig in [t[0] for t in fosids_g]:
                    fos_name_d = fos_name_map[fid]
                    fos_name_g = fos_name_map[fig]
                    fos_pair_name = '{}->{}'.format(fos_name_g, fos_name_d)
                    if fos_pair_name not in both_fos_count_map:
                        both_fos_count_map[fos_pair_name] = 0
                    both_fos_count_map[fos_pair_name] += 1
                    if fig in lvl0fos_ids and fid in lvl0fos_ids:
                        if fos_pair_name not in both_fos_count_map_basic:
                            both_fos_count_map_basic[fos_pair_name] = 0
                        both_fos_count_map_basic[fos_pair_name] += 1

cited_fos_counts = sorted(
    cited_fos_count_map.items(),
    key=operator.itemgetter(1),
    reverse=True
    )
cited_fos_counts_basic = sorted(
    cited_fos_count_map_basic.items(),
    key=operator.itemgetter(1),
    reverse=True
    )

with open('cited_fos_counts.json', 'w') as f:
    f.write(json.dumps(cited_fos_counts))
with open('cited_fos_counts_basic.json', 'w') as f:
    f.write(json.dumps(cited_fos_counts_basic))

citing_fos_counts = sorted(
    citing_fos_count_map.items(),
    key=operator.itemgetter(1),
    reverse=True
    )
citing_fos_counts_basic = sorted(
    citing_fos_count_map_basic.items(),
    key=operator.itemgetter(1),
    reverse=True
    )

with open('citing_fos_counts.json', 'w') as f:
    f.write(json.dumps(citing_fos_counts))
with open('citing_fos_counts_basic.json', 'w') as f:
    f.write(json.dumps(citing_fos_counts_basic))

both_fos_counts = sorted(
    both_fos_count_map.items(),
    key=operator.itemgetter(1),
    reverse=True
    )
both_fos_counts_basic = sorted(
    both_fos_count_map_basic.items(),
    key=operator.itemgetter(1),
    reverse=True
    )

with open('both_fos_counts.json', 'w') as f:
    f.write(json.dumps(both_fos_counts))
with open('both_fos_counts_basic.json', 'w') as f:
    f.write(json.dumps(both_fos_counts_basic))
