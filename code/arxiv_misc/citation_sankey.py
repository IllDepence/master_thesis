import json
import plotly
import matplotlib as mpl

with open('citation_fos_pairs_fixed_fixed_2018.json') as f:
    tups = json.load(f)

from_to_map = {}
from_to_physcomb_map = {}
arx_remap = {
    'cs': 'computer science',
    'math': 'mathematics',
    'eess': 'other',
    'q-bio': 'other',
    'stat': 'other',
    'q-fin': 'other',
    'econ': 'other'
    }
# arx_remap = {
#     'cs': 'computer science',
#     'math': 'mathematics',
#     'eess': 'electrical engineering and systems science',
#     'q-bio': 'quantitive biology',
#     'econ': 'economics'
#     }
out_labels = []
in_labels = []
for tup in tups:
    # orig
    fos_arx = tup[0]
    fos_mag = tup[1]
    if not fos_arx in from_to_map:
        from_to_map[fos_arx] = {}
    if not fos_mag in from_to_map[fos_arx]:
        from_to_map[fos_arx][fos_mag] = 0
    from_to_map[fos_arx][fos_mag] += 1
    # modified
    if 'physics' in fos_arx:
        fos_arx = 'physics'
    elif fos_arx in arx_remap:
        fos_arx = arx_remap[fos_arx]
    if fos_mag not in ['computer science', 'physics', 'mathematics']:
        fos_mag = 'other'
    if not fos_arx in from_to_physcomb_map:
        from_to_physcomb_map[fos_arx] = {}
    if not fos_mag in from_to_physcomb_map[fos_arx]:
        from_to_physcomb_map[fos_arx][fos_mag] = 0
    from_to_physcomb_map[fos_arx][fos_mag] += 1
    # ---
    if not fos_arx in out_labels:
        out_labels.append(fos_arx)
    if not fos_mag in in_labels:
        in_labels.append(fos_mag)

label = out_labels+in_labels
palette = [x['color'] for x in list(mpl.rcParams['axes.prop_cycle'])]*10
color = []
for idx, l in enumerate(label):
    if l in out_labels:
        color.append(palette[out_labels.index(l)])
    else:
        color.append(palette[len(out_labels)+in_labels.index(l)])
source = []
target = []
value = []
link_color = []
for fos_arx, val in from_to_physcomb_map.items():
    # print('{}:'.format(fos_arx))
    for fos_mag, count in val.items():
        source.append(out_labels.index(fos_arx))
        target.append(len(out_labels)+in_labels.index(fos_mag))
        value.append(count)
        link_color.append('{}88'.format(palette[out_labels.index(fos_arx)]))
        # print('  --[{}]--> {}'.format(count, fos_mag))

data = dict(
    type='sankey',
    node = dict(
      pad = 0,
      thickness = 20,
      line = dict(
        color = 'black',
        width = 0.1
      ),
      label = label,
      color = color
    ),
    link = dict(
      color = link_color,
      source = source,
      target = target,
      value = value
  ))

layout =  dict(
    title = 'citation relations',
    font = dict(
      size = 20
    )
)

fig = dict(data=[data], layout=layout)
plotly.offline.plot(fig, validate=False)
