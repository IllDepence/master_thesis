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

    # count_map = {}
    x = []
    y = []

    # Ｆ　Ｉ　Ｘ　Ｍ　Ｅ
    #  FIXME: below only calculates in how many *DOCUMENTS* a context appears
    #  FIXME: and disregards multiple contexts in a single document
    # Ｆ　Ｉ　Ｘ　Ｍ　Ｅ

    # for count in range(1, 11):
    for count in range(50, 151):
        res = session.query(BibitemArxivIDMap.arxiv_id).\
                    group_by(BibitemArxivIDMap.arxiv_id).\
                    having(func.count(BibitemArxivIDMap.arxiv_id) == count).\
                    all()
        x.append(count)
        y.append(len(res))
        # count_map[count] = len(res)

    fig, ax = plt.subplots()
    plt.bar(x, y, align='center', alpha=0.5)
    ax.grid(color='lightgray', linestyle='--', linewidth=0.5)
    ax.set_xlabel('# citation contexts')
    ax.set_ylabel('citations')
    # plt.xticks(np.arange(1, 11, step=1))
    # plt.yticks(np.arange(0, 40001, step=5000))
    # for i, j in zip(x, y):
    #     ax.annotate(str(j), xy=(i-0.14,j+600+(len(str(j))*700)), color='grey', rotation=90)
    plt.show()
    # with open('count_map.json', 'w') as f:
    #     f.write(json.dumps(count_map))

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
