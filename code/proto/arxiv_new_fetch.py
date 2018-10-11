""" do stuff w/ the arXiv metadata xml file
"""

from lxml import etree

parser = etree.XMLParser(ns_clean=True)
with open('arxiv-cs-all-until201712031.xml') as f:
    tree = etree.parse(f, parser)

# number of DOIs
r = tree.xpath("//dc:identifier[starts-with(text(),'doi')]",
               namespaces={'dc':'http://purl.org/dc/elements/1.1/'})

# "//record/metadata/dc:identifier[starts-with(text(),'doi')]"
# for some reason doesn't work

# "//record//metadata//dc:identifier[starts-with(text(),'doi')]"
# is too loose and takes ages to evaluate
