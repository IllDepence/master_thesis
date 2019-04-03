import re
from nltk import pos_tag
# from nltk.corpus import wordnet
# from nltk.stem import WordNetLemmatizer
from gensim.parsing.preprocessing import (strip_multiple_whitespaces,
                                          strip_punctuation,
                                          remove_stopwords)


# def get_wordnet_pos(treebank_tag):
#     if treebank_tag.startswith('J'):
#         return wordnet.ADJ
#     elif treebank_tag.startswith('V'):
#         return wordnet.VERB
#     elif treebank_tag.startswith('R'):
#         return wordnet.ADV
#     else:
#         return wordnet.NOUN


def bow_preprocess_string(s):
    """ Preprocessing of strings to be used for gensim dictionary generation
        and for turning test set strings into BOWs.

        - remove substitution tokens
        - remove punctuation
        - remove multiple whitespaces
        (- lemmatize   too time consuming for full dataset in given time)
        - remove stopwords
    """

    token_patt = r'(MAINCIT|CIT|FORMULA|REF|TABLE|FIGURE)'
    # wordnet_lemmatizer = WordNetLemmatizer()
    s = re.sub(token_patt, ' ', s)
    s = strip_punctuation(s)
    s = strip_multiple_whitespaces(s)
    # words = [wordnet_lemmatizer.lemmatize(
    #              w[0],
    #              pos=get_wordnet_pos(w[1])
    #              )
    #          for w in pos_tag(s.split())]
    # s = remove_stopwords(' '.join(words))
    s = remove_stopwords(s)
    return s.split()
