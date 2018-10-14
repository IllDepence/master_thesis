""" texsoup experiment
"""

import os
import re
import sys
from TexSoup import TexSoup

IN_DIR = sys.argv[1]
BEGIN_DOC_PATT = re.compile(r'\\begin\s*\{\s*document\s*\}', re.I)
NICE_HEAD = '\\documentclass[12pt]{article}\n\\begin{document}\n'

def defuse_preamble(tex):
    parts = re.split(BEGIN_DOC_PATT, tex, maxsplit=1)
    return '{}{}'.format(NICE_HEAD, parts[1])

wins = 0
defuses = 0
fails = 0
for fn in os.listdir(IN_DIR):
    if fn[-4:] == '.pdf':
        continue
    msg = fn
    path = os.path.join(IN_DIR, fn)
    try:
        with open(path) as f:
            tex = f.read()
    except Exception as e:
        fails += 1
        msg += ' ✗✗✗'
        with open('open_fails.txt', 'a') as f:
            f.write('\n--- {} ---\n{}\n'.format(fn, e))
        print(msg)
    try:
        soup = TexSoup(tex)
        wins += 1
        msg += ' ✔'
    except:
        try:
            soup = TexSoup(defuse_preamble(tex))
            defuses += 1
            msg += ' ✔ (defused)'
        except Exception as e:
            fails += 1
            msg += ' ✗'
            with open('soup_fails.txt', 'a') as f:
                f.write('\n--- {} ---\n{}\n'.format(fn, e))
    print(msg)

print('wins: {}'.format(wins))
print('defuses: {}'.format(defuses))
print('fails: {}'.format(fails))
