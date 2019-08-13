""" Compare citation mappings between papers in
    - the MAG itself
    - unarXive

    all links:     15,846,351
    matching_links: 9,882,069
        -> 62% of unarXive links found in MAG
        -> unarXive has 60% more (160%) citation interlinkgs
            -> are they correct and therefore missing in the MAG?
"""

from sqlalchemy import create_engine

ua_db_uri = 'sqlite:////home/saiert/arxiv_v2.1.1_refs.db'
ua_engine = create_engine(ua_db_uri)  #, connect_args={'timeout': 60}

m_db_uri = 'postgresql+psycopg2://mag:1maG$@localhost:5432/MAG19'
m_engine = create_engine(m_db_uri)  #,
#    connect_args={'options': '-c statement_timeout=60000'}
#    )

qa = ('SELECT citing_mag_id, cited_mag_id, citing_arxiv_id, cited_arxiv_id FROM bibitem'
      ' WHERE citing_mag_id IS NOT NULL and cited_mag_id IS NOT NULL')
tups = ua_engine.execute(qa).fetchall()

all_links = len(tups)
matching_links = 0
with open('missing_links.txt', 'w') as f:
    for i, tup in enumerate(tups):
        if i%10000 == 0:
            print('{}/{} ({}) ({} matches)'.format(i, all_links, i/all_links, matching_links))
        citing_mid = tup[0]
        cited_mid = tup[1]
        citing_aid = tup[2]
        cited_aid = tup[3]
        qm = ('SELECT * FROM paperreferences'
              ' WHERE paperid = \'{}\' and paperreferenceid = \'{}\''
              ).format(citing_mid, cited_mid)
        res = m_engine.execute(qm).fetchone()
        if res and len(res) > 0:
            matching_links += 1
        else:
            f.write('{},{},{},{}\n'.format(citing_mid, cited_mid, citing_aid, cited_aid))

print('all links: {}'.format(all_links))
print('matching_links: {}'.format(matching_links))
