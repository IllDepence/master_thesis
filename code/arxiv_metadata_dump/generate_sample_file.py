""" Generate a file sample.json from a metadata dump, that lists a random
    100/<FRACTION> % of all publications while preserving the distribution
    of publications per months and per discipline per month.
"""

import os
import json
from lxml import etree
from random import shuffle

FRACTION = 100

ns = {'oai':'http://www.openarchives.org/OAI/2.0/',
      'dc':'http://purl.org/dc/elements/1.1/',
      'oai_dc':'http://www.openarchives.org/OAI/2.0/oai_dc/',
      'xsi':'http://www.w3.org/2001/XMLSchema-instance'}

parser = etree.XMLParser()
dump_dir = '/vol1/arxiv/metadata/newArxivMetaHarvesting201712'

month_field_docs = {}
for fn in os.listdir(dump_dir):
    if os.path.splitext(fn)[1] != '.xml':
        continue
    path = os.path.join(dump_dir, fn)
    with open(path) as f:
        tree = etree.parse(f, parser)
    for rec in tree.xpath('/oai:OAI-PMH/oai:ListRecords/oai:record',
                          namespaces=ns):
        header = rec.find('oai:header', namespaces=ns)
        field = header.find('oai:setSpec', namespaces=ns).text
        field = field.split(':')[0]
        id_text = header.find('oai:identifier', namespaces=ns).text
        aid = id_text.split(':')[-1]
        # aid_fn = aid.replace('/', '')
        meta = rec.find('oai:metadata', namespaces=ns)
        try:
            first_date = meta.getchildren()[0].find('dc:date', namespaces=ns).text
        except AttributeError:
            continue
        month = first_date[2:4] + first_date[5:7]
        if month not in month_field_docs:
            month_field_docs[month] = {}
        if field not in month_field_docs[month]:
            month_field_docs[month][field] = []
        month_field_docs[month][field].append(aid)

sample = {}
for month, field_docs in month_field_docs.items():
    # print(month)
    if month not in sample:
        sample[month] = []
    for field, docs in field_docs.items():
        # print(field)
        total = len(docs)
        sample_size = round(total/FRACTION)
        shuffle(docs)
        # print('{} -> {}'.format(total, sample_size))
        sample[month].extend(docs[:sample_size])
        # input()

with open('sample.json', 'w') as f:
    json.dump(sample, f)
