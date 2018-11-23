import os
import json
fns = os.listdir('.')
fos_map = {}
for fn in fns:
  with open(fn) as f:
    lines = f.readlines()
  foss = lines[0].split(' ')
  foss = [f.strip() for f in foss]
  mid = fn.replace('.out', '')
  fos_map[mid] = foss
fos_map
with open('mid_map.json', 'w') as f:
  f.write(json.dumps(fos_map))
