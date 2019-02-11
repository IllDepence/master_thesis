import os
import regex
import sys

sqr_brck = regex.compile(
    r'\[\s*((\p{Lu}\p{Ll}{0,10})?\d{1,4})(\s*(-|,)\s*((\p{Lu}\p{Ll}{0,10})?\d{1,4}))*\s*\]'
    )
rnd_brck = regex.compile(
    r'\(\s*\p{Lu}\p{Ll}[^\(]*\s*[,.:;]\s*\d{2,4}\s*\)'
    )
name_date = regex.compile(
    r'(((\p{Lu}\p{Ll}{1,4})?\p{Lu}\p{Ll}{1,}(\s+(((\p{Lu}\p{Ll}{1,4})?\p{Lu}\p{Ll}{1,})|(\p{Lu}[.,])))*)(\s*([,;.])\s*)?(\s*(and|&)\s*)?)+(\s*et\.?\s*al\.?\s*)?\s*[,.]?\s*[\(\[]?\s*[12][0-9]{3}[a-z]?\s*[\)\]]?'
    )

in_file = sys.argv[1]
in_n = os.path.splitext(in_file)[0]
out_file = '{}_stripped.csv'.format(in_n)

with open(in_file) as fi:
    with open(out_file, 'w') as fo:
        for i, line in enumerate(fi):
            if i%10000 == 0:
                print(i)
            cited_mid, empty, citing_mid, context = line.split('\u241E')
            # context = rnd_brck.sub(' ', context)
            context = name_date.sub(' ', context)
            context = sqr_brck.sub(' ', context)
            context = '{}\n'.format(context.strip())
            line_fixed = '{}'.format(
                '\u241E'.join([cited_mid, empty, citing_mid, context])
                )
            fo.write(line_fixed)
