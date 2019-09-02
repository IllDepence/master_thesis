import os
import sys
import pickle
from nltk.tokenize.punkt import PunktSentenceTokenizer, PunktTrainer

in_dir = sys.argv[1]
print('folder: {}'.format(in_dir))
print('ok?')
input()
fns = os.listdir(in_dir)
trainer = PunktTrainer()
# trainer.INCLUDE_ALL_COLLOCS = True
for idx, fn in enumerate(fns):
    try:
        if idx%1000 == 0:
            print('{}/{}'.format(idx, len(fns)))
        nm, ext = os.path.splitext(fn)
        if ext != '.txt':
            continue
        fp = os.path.join(in_dir, fn)
        with open(fp) as f:
            text = f.read()
        trainer.train(text, finalize=False, verbose=False)
    except KeyboardInterrupt:
        print('MANUALLY ABORTED')
        break

trainer.finalize_training(verbose=True)
tokenizer = PunktSentenceTokenizer(trainer.get_params())

print('pickling ...')
with open('arXiv_sentence_tokenizer.pickle', 'wb') as f:
    pickle.dump(tokenizer, f)
