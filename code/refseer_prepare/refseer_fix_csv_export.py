import csv
import regex
import sys

in_file = sys.argv[1]
out_file = sys.argv[2]

sqr_brck = regex.compile(
    r'\[\s*((\p{Lu}\p{Ll}{0,10})?\d{1,4})(\s*(-|,)\s*((\p{Lu}\p{Ll}{0,10})?\d{1,4}))*\s*\]'
    )
name_date = regex.compile(
    r'(((\p{Lu}\p{Ll}{1,4})?\p{Lu}\p{Ll}{1,}(\s+(((\p{Lu}\p{Ll}{1,4})?\p{Lu}\p{Ll}{1,})|(\p{Lu}[.,])))*)(\s*([,;.])\s*)?(\s*(and|&)\s*)?)+(\s*et\.?\s*al\.?\s*)?\s*[,.]?\s*[\(\[]?\s*[12][0-9]{3}[a-z]?\s*[\)\]]?'
    )

with open(in_file) as f:
    with open(out_file, 'w') as fo:
        csvreader = csv.reader(f, delimiter=',', quotechar='"')
        for row in csvreader:
            if len(row) < 6:
                print(row)
                sys.exit()
            # cited_id, cited_year, citing_id, citing_year, citing_title, context
            row = row[0:5] + [','.join(row[5:])]
            # can't use 200 character offset b/c csv.reader strips trailing
            # (any mabye also leading?) whitespace
            row[5] = name_date.sub(' ', row[5])
            row[5] = sqr_brck.sub(' ', row[5])
            combo_citing_id = '{}_{}'.format(row[3], row[2])
            new_line = '{}\n'.format(
                '\u241E'.join([row[0], '', combo_citing_id, row[5]])
                )
            fo.write(new_line)
