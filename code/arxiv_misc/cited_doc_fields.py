import numpy as np
import matplotlib.pyplot as plt

s = """  mathematics: 852206
  computer science: 293971
  physics: 893950
  materials science: 28944
  business: 4231
  engineering: 31148
  psychology: 18322
  medicine: 12777
  geography: 4103
  history: 838
  economics: 26882
  biology: 67194
  political science: 2514
  sociology: 3034
  environmental science: 1645
  chemistry: 78102
  philosophy: 2173
  geology: 18330
  art: 858"""

lines = s.split('\n')
label_val_tups = []
for line in lines:
    parts = line.split(': ')
    label_val_tups.append((parts[0].strip(), int(parts[1].strip())))
label_val_tups = sorted(label_val_tups, key=lambda x: x[1])
labels = []
values = []
vals_total = 0
for tup in label_val_tups:
    labels.append(tup[0])
    values.append(tup[1])
    vals_total += tup[1]
print(labels)
print(values)
ax = plt.subplot()
ax.barh(labels, values, .8, color='grey')
for i, v in enumerate(values):
    ax.text(v + 10000, i -.25, '{} ({:.2f}%)'.format(v, (v/vals_total)*100), color='black')
plt.title('fields of study of cited docs')
plt.xlabel('number of documents')
plt.tight_layout()
ax.spines['right'].set_visible(False)
ax.get_xaxis().set_visible(False)
plt.show()
