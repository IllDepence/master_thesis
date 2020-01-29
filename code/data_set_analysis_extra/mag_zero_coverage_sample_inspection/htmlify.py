import re
import sys

mag_pref = '<a href="https://academic.microsoft.com/paper/'

with open(sys.argv[1]) as fi:
    with open('htmlified.html', 'w') as fo:
        fo.write('<html><body>')
        for i, line in enumerate(fi):
            citing_id, cited_s = line.strip().split('\t')
            cited_list = cited_s.split(',')
            citing_link = '{}{}">MAG</a>'.format(mag_pref, citing_id)
            cited_links = ['{}{}">MAG</a>'.format(mag_pref, cited_id) for cited_id in cited_list]
            cited_link_s = ', '.join(cited_links)
            html_line = '<p>{}: {}&emsp;→&emsp;{}</p>'.format(i, citing_link, cited_link_s)
            fo.write(html_line)
        fo.write('</body></html>')
