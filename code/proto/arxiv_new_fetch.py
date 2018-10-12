""" do stuff w/ the arXiv metadata xml file
"""

from lxml import etree

parser = etree.XMLParser()
with open('arxiv-cs-all-until201712031.xml') as f:
    tree = etree.parse(f, parser)

ns = {'dc':'http://purl.org/dc/elements/1.1/',
      'oai_dc':'http://www.openarchives.org/OAI/2.0/oai_dc/',
      'xsi':'http://www.w3.org/2001/XMLSchema-instance'}

# number of DOIs
r = tree.xpath(("/ListRecords/record/metadata/oai_dc:dc/dc:identifier[starts-w"
                "ith(text(),'doi')]"), namespaces=ns)
print('number of DOIs: {}'.format(len(r)))
# 29739

# number of records
r = tree.xpath("/ListRecords/record")
print('number of records: {}'.format(len(r)))
# 155308
