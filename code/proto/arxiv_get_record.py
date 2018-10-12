""" do stuff w/ the arXiv metadata xml file
"""

import sys
from lxml import etree

parser = etree.XMLParser()
with open('arxiv-cs-all-until201712031.xml') as f:
    tree = etree.parse(f, parser)
# -> ~3.5s

xp = "/ListRecords/record/header/identifier[text()='{}']".format(sys.argv[1])
print(xp)
r = tree.xpath(xp)
# -> >0.1s

print(etree.tostring(r[0].getparent()))
