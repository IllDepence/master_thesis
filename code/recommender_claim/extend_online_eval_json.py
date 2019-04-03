import json
import sys
from sqlalchemy import create_engine

def get_paper_info(mid, db_engine):
    tuples = db_engine.execute(
        ('select originaltitle, publishedyear, citationcount from papers where paperid = {}').format(mid)
        ).fetchall()
    return tuples[0]

def get_abstract(mid, db_engine):
    tuples = db_engine.execute(
        ('select abstract from paperabstracts where paperid = {}').format(mid)
        ).fetchall()
    if len(tuples) == 0:
        return ''
    return tuples[0][0]

mag_db_uri = 'postgresql+psycopg2://mag:1maG$@localhost:5432/MAG'
mag_engine = create_engine(mag_db_uri,
    connect_args={'options': '-c statement_timeout=60000'}
    )

with open(sys.argv[1]) as f:
    lisd = json.load(f)

new_list = []
for item in lisd:
    new_item = {}
    new_item['context'] = item['context']
    methods = [('bow', item['bow']), ('pp', item['pp'])]
    if 'np' in item:
        methods.append(('np', item['np']))
    for name, ranking in methods:
        new_item[name] = []
        for mid in ranking:
            title, year, citcount = get_paper_info(mid, mag_engine)
            abstract = get_abstract(mid, mag_engine)
            new_item[name].append([mid, title, year, citcount, abstract])
    new_list.append(new_item)

with open('more_extended_online_eval_recomms.json', 'w') as f:
    f.write(json.dumps(new_list))
