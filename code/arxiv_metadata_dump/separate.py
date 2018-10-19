import os
from lxml import etree

ns = {'oai':'http://www.openarchives.org/OAI/2.0/',
      'dc':'http://purl.org/dc/elements/1.1/',
      'oai_dc':'http://www.openarchives.org/OAI/2.0/oai_dc/',
      'xsi':'http://www.w3.org/2001/XMLSchema-instance'}

parser = etree.XMLParser()

if not os.path.isdir('single'):
    os.makedirs('single')

for fn in os.listdir(os.getcwd()):
    if os.path.splitext(fn)[1] != '.xml':
        continue
    with open(fn) as f:
        tree = etree.parse(f, parser)
    for rec in tree.xpath('/oai:OAI-PMH/oai:ListRecords/oai:record',
                          namespaces=ns):
        header = rec.find('oai:header', namespaces=ns)
        id_text = header.find('oai:identifier', namespaces=ns).text
        aid = id_text.split(':')[-1]
        aid_fn = aid.replace('/', '')
        meta = rec.find('oai:metadata', namespaces=ns)
        try:
            meta_bytes = etree.tostring(meta, pretty_print=True)
        except TypeError as e:
            print('problem with {} in {}:\n{}'.format(aid, fn, e))
            continue
        with open('single/{}.xml'.format(aid_fn), 'wb') as f:
            f.write(meta_bytes)
