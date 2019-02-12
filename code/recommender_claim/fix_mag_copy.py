import os
import re
import sys

patt = re.compile(r'^(\d+),(\d+),"?(.+?)"?$')

in_file = sys.argv[1]
in_n = os.path.splitext(in_file)[0]
out_file = '{}_fixed.csv'.format(in_n)

with open(in_file) as fi:
    with open(out_file, 'w') as fo:
        for i, line in enumerate(fi):
            if i%10000 == 0:
                print(i)
            m = patt.match(line)
            if m == None:
                # empty citation context, skip
                continue
            cited_mid = m.group(1)
            citing_mid = m.group(2)
            context = m.group(3)
            line_fixed = '{}\n'.format(
                '\u241E'.join([cited_mid, '', citing_mid, context])
                )
            fo.write(line_fixed)
