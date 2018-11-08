""" Distribution of count of citation contexts per cited doc
"""

import json
import os
import re
import sys
import numpy as np
import matplotlib.pyplot as plt
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from db_model import Base, Bibitem, BibitemArxivIDMap


def generate(in_dir, db_uri=None):
    if not db_uri:
        db_path = os.path.join(in_dir, 'metadata.db')
        db_uri = 'sqlite:///{}'.format(os.path.abspath(db_path))
    engine = create_engine(db_uri)
    Base.metadata.create_all(engine)
    Base.metadata.bind = engine
    DBSession = sessionmaker(bind=engine)
    session = DBSession()

    count_map = {}
    x = []
    y = []

    print('querying DB')
    sub = session.query(BibitemArxivIDMap.arxiv_id).\
                subquery()
    res = session.query(Bibitem, BibitemArxivIDMap).\
                filter(Bibitem.uuid == BibitemArxivIDMap.uuid).\
                filter(BibitemArxivIDMap.arxiv_id.in_(sub)).\
                all()
    print('merging bibitems')
    cited_docs = {}
    for bibitem in res:
        aid = bibitem.BibitemArxivIDMap.arxiv_id
        if aid not in cited_docs:
            cited_docs[aid] = []
        cited_docs[aid].append({
            'uuid': bibitem.Bibitem.uuid,
            'in_doc': bibitem.Bibitem.in_doc
            })
    print('going through docs')
    for aid, doc_list in cited_docs.items():
        count = 0
        for doc in doc_list:
            fn = '{}.txt'.format(doc['in_doc'])
            text_file = os.path.join(in_dir, fn)
            with open(text_file) as f:
                text = f.read()
            marker = '{{{{cite:{}}}}}'.format(doc['uuid'])
            count += text.count(marker)
        if count < 1:
            # NOTE: count is 0 in rare cases b/c of citation styles like
            #       \cite{radice:2013hxh, *radice:2013xpa} in 1712.04267,
            #       where the latter does not end up in the .txt even though
            #       appearing in the DB
            continue
        if count not in count_map:
            count_map[count] = 0
        count_map[count] += 1
    # with open('count_map.json', 'w') as f:
    #     f.write(json.dumps(count_map))

    for count in range(2, 21):
        if count in count_map:
            x.append(count)
            y.append(count_map[count])

    fig, ax = plt.subplots()
    plt.bar(x, y, align='center', alpha=0.5)
    ax.grid(color='lightgray', linestyle='--', linewidth=0.5)
    ax.set_xlabel('# citation contexts')
    ax.set_ylabel('citations')
    plt.xticks(np.arange(2, 21, step=1))
    plt.yticks(np.arange(0, 12001, step=2000))
    for i, j in zip(x, y):
        ax.annotate(str(j), xy=(i-0.23,j+1000+(j*0.05)),
                    color='grey', rotation=90)
    plt.show()

if __name__ == '__main__':
    if len(sys.argv) not in [2, 3]:
        print(('usage: python3 ___.py </path/to/in/dir> [<db_uri>'
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
