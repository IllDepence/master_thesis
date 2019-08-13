import re

arxiv_pref = '<a href="https://arxiv.org/pdf/'
mag_pref = '<a href="https://academic.microsoft.com/paper/'

with open('missing_links_sample') as fi:
    with open('missing_links_sample.html', 'w') as fo:
        fo.write('<html><body>')
        for i, line in enumerate(fi):
            cg_mid, cd_mid, cg_aid, cd_aid = line.strip().split(',')
            m = re.search('\d', cg_aid)
            if m and m.start() > 0:
                cg_aid = '{}/{}'.format(cg_aid[:m.start()], cg_aid[m.start():])
            m = re.search('\d', cd_aid)
            if m and m.start() > 0:
                cd_aid = '{}/{}'.format(cd_aid[:m.start()], cd_aid[m.start():])
            cg_m_link = '{}{}">MAG</a>'.format(mag_pref, cg_mid)
            cd_m_link = '{}{}">MAG</a>'.format(mag_pref, cd_mid)
            cg_a_link = '{}{}">arXiv</a>'.format(arxiv_pref, cg_aid)
            if cd_aid == 'None':
                cd_a_link = ''
            else:
                cd_a_link = '{}{}">arXiv</a>'.format(arxiv_pref, cd_aid)
            html_line = '<p>{}: {}→{} / {}→{}</p>'.format(i, cg_m_link, cd_m_link, cg_a_link, cd_a_link)
            fo.write(html_line)
        fo.write('</body></html>')
