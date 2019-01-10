""" Code snippets
"""

import nltk
import re
import numpy as np
from nltk.cluster import KMeansClusterer
from gensim import corpora, models, similarities
from gensim.models import Word2Vec
from nltk.stem.snowball import SnowballStemmer

stemmer = SnowballStemmer('english')

def tokenize_and_stem(text):
    # first tokenize by sentence, then by word to ensure that punctuation is
    # caught as it's own token
    tokens = [word for sent in nltk.sent_tokenize(text)
        for word in nltk.word_tokenize(sent)
        ]
    filtered_tokens = []
    # filter out any tokens not containing letters (e.g., numeric tokens,
    # raw punctuation)
    for token in tokens:
        if re.search('[a-zA-Z]', token):
            filtered_tokens.append(token)
    stems = [stemmer.stem(t) for t in filtered_tokens]
    return stems

# setup
with open('items_mini.csv') as f:
  lines = f.readlines()

texts = []
for l in lines:
  texts.append(l.split(',')[-1].strip().replace('[]', ''))

stopwords = nltk.corpus.stopwords.words('english')
stopwords.append('FORMULA')
stopwords.append('FIGURE')
stopwords.append('TABLE')

tokenized_text = [tokenize_and_stem(text) for text in texts]
texts_tok = [[word for word in text if word not in stopwords] for text in tokenized_text]
dictionary = corpora.Dictionary(texts_tok)
corpus = [dictionary.doc2bow(text) for text in texts_tok]

# TFIDF
tfidf = models.TfidfModel(corpus)
tfidf.num_docs
num_unique_tokens = len(dictionary.keys())
index = similarities.SparseMatrixSimilarity(tfidf[corpus],
        num_features=num_unique_tokens)
test_bow = dictionary.doc2bow('This is just a test'.split())
sims = index[tfidf[test_bow]]

# LDA
lda = models.LdaModel(corpus, num_topics=5,
                            id2word=dictionary,
                            update_every=5,
                            chunksize=10000,
                            passes=100)
print(lda.show_topics())

# k-means
model = Word2Vec(texts_tok, min_count=1)
X = model[model.wv.vocab]
NUM_CLUSTERS=5
kclusterer = KMeansClusterer(NUM_CLUSTERS,
                             distance=nltk.cluster.util.cosine_distance,
                             repeats=100)
assigned_clusters = kclusterer.cluster(X, assign_clusters=True)
print(assigned_clusters)
words = list(model.wv.vocab)
for i, word in enumerate(words):
    print (word + ":" + str(assigned_clusters[i]))
