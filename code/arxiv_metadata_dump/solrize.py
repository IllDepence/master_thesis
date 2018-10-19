import os
from lxml import etree

ns = {'oai':'http://www.openarchives.org/OAI/2.0/',
      'dc':'http://purl.org/dc/elements/1.1/',
      'oai_dc':'http://www.openarchives.org/OAI/2.0/oai_dc/',
      'xsi':'http://www.w3.org/2001/XMLSchema-instance'}

parser = etree.XMLParser()

if not os.path.isdir('solrized'):
    os.makedirs('solrized')

for fn in os.listdir(os.getcwd()):
    if os.path.splitext(fn)[1] != '.xml':
        continue
    with open(fn) as f:
        tree = etree.parse(f, parser)
    new_root = etree.Element('add')
    for rec in tree.xpath('/oai:OAI-PMH/oai:ListRecords/oai:record',
                          namespaces=ns):
        header = rec.find('oai:header', namespaces=ns)
        id_text = header.find('oai:identifier', namespaces=ns).text
        aid = id_text.split(':')[-1]
        aid_fn = aid.replace('/', '')
        meta = rec.find('oai:metadata', namespaces=ns)
        if meta is None:
            print('no metadata in {} in {}'.format(aid, fn))
            continue
        new_doc = etree.SubElement(new_root, 'doc')
        dc = meta.find('oai_dc:dc', namespaces=ns)
        for elem in dc.getchildren():
            name = elem.tag.split('}')[-1]  # dirty
            new_elem = etree.Element('field', name=name)
            new_elem.text = elem.text
            new_doc.append(new_elem)
        new_root.append(new_doc)
    new_xml = etree.tostring(new_root, pretty_print=True)
    with open('solrized/{}'.format(fn), 'wb') as f:
        f.write(new_xml)
