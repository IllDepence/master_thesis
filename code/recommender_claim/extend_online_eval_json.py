import json
import sys
from sqlalchemy import create_engine

def get_title(mid, db_engine):
    tuples = db_engine.execute(
        ('select originaltitle from papers where paperid = {}').format(mid)
        ).fetchall()
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
            title = get_title(mid, mag_engine)
            new_item[name].append([mid, title])
    new_list.append(new_item)

with open('extended_online_eval_recomms.json', 'w') as f:
    f.write(json.dumps(new_list))
