import re
import signal
import sys
import zlib
import numpy as np
from operator import itemgetter
from predpatt import PredPatt

MAINCITS_PATT = re.compile(r'((CIT , )*MAINCIT( , CIT)*)')
CITS_PATT = re.compile(r'(((?<!MAIN)CIT , )*(?<!MAIN)CIT( , (?<!MAIN)CIT)*)')
TOKEN_PATT = re.compile(r'(MAINCIT|CIT|FORMULA|REF|TABLE|FIGURE)')
QUOTMRK_PATT = re.compile(r'[“”„"«»‹›《》〈〉]')


def signal_handler(signum, frame):
    raise Exception('Timed out!')


def merge_citation_token_lists(s):
    s = MAINCITS_PATT.sub('MAINCIT', s)
    s = CITS_PATT.sub('CIT', s)
    return s


def remove_qutation_marks(s):
    return QUOTMRK_PATT.sub('', s)


def get_maincit(root_node, found_node=None):
    """ Traverse a PredPatt event tree and return MAINCIT node if contained.
    """

    if found_node:
        return found_node
    for d in root_node.dependents:
        if d.gov.text == 'MAINCIT':
            return d.gov
        if d.dep.text == 'MAINCIT':
            return d.dep
        found_node = get_maincit(d.dep, found_node)
    return found_node


def compound_text_variations(node):
    """ Return representational variants of a node depending on it being part
        of a name, fixed expression or compound or having adjectival modifiers
        (which, in turn, themselves can have adverbial modifiers).
        Also poorly handles conjunctions.

        Return format is a list with growing phrase size. Example:
            ['datasets', 'large-scale datasets',
             'available large-scale datasets',
             'publicly available large-scale datasets']
    """

    tag_blacklist = ['PRON', 'DET', 'VERB', 'NUM']

    texts = ['']  # to make the [-1] indexing happy (filtered out at the end)
    if node.tag not in tag_blacklist:
        texts.append(node.text)

    # names
    for d in node.dependents:
        if d.rel == 'name' and d.dep.tag not in tag_blacklist:
            texts.append('{} {}'.format(texts[-1], d.dep.text))
    # goeswith
    for d in node.dependents:
        if d.rel == 'goeswith' and d.dep.tag not in tag_blacklist:
            texts.append('{} {}'.format(texts[-1], d.dep.text))
    # multi word expressions
    for d in node.dependents:
        if d.rel == 'mwe' and d.dep.tag not in tag_blacklist:
            texts.append('{} {}'.format(d.dep.text, texts[-1]))
    # compounds
    for d in node.dependents[::-1]:
        if d.rel == 'compound' and d.dep.tag not in tag_blacklist:
            texts.append('{} {}'.format(d.dep.text, texts[-1]))
            # conjunctions
            for dd in d.dep.dependents:
                if dd.rel == 'conj' and dd.dep.tag not in tag_blacklist:
                    # TODO: this could be done in a way such that a copy of all
                    #       following modifiers is created with the conjunct
                    texts.append('{} {}'.format(dd.dep.text, texts[-2]))
    # adjective modifiers
    for d in node.dependents[::-1]:
        if d.rel == 'amod' and d.dep.tag not in tag_blacklist:
            texts.append('{} {}'.format(d.dep.text, texts[-1]))
            # conjunctions
            for dd in d.dep.dependents:
                if dd.rel == 'conj' and dd.dep.tag not in tag_blacklist:
                    # TODO: this could be done in a way such that a copy of all
                    #       following modifiers is created with the conjunct
                    texts.append('{} {}'.format(dd.dep.text, texts[-2]))
            # adverbial modifiers of adjective modifiers
            for dd in d.dep.dependents:
                if dd.rel == 'advmod' and dd.dep.tag not in tag_blacklist:
                    texts.append('{} {}'.format(dd.dep.text, texts[-1]))
                for ddd in dd.dep.dependents:
                    if ddd.rel == 'conj' and ddd.dep.tag not in tag_blacklist:
                        # TODO: this could be done in a way such that a copy of
                        #       all following modifiers is created with the
                        #       conjunct
                        texts.append('{} {}'.format(ddd.dep.text, texts[-2]))

    # clean
    texts = [TOKEN_PATT.sub('', t).strip() for t in texts]
    texts = [re.sub('\s+', ' ', t) for t in texts]
    return [t for t in texts if len(t) > 0]


def is_example_for(node):
    """ Detect if the node is mentioned being an example for something. If so,
        return the node that the input note is an example for.

        Currently only handles "such as" constructs.
    """

    has_such_as = False
    for d in node.dependents:
        if d.rel == 'case' and d.dep.text == 'such':
            such_node = d.dep
            for dd in such_node.dependents:
                if dd.rel == 'mwe' and dd.dep.text == 'as':
                    has_such_as = True
    if has_such_as and node.gov_rel == 'nmod':
        return node.gov
    return None


def build_tree_representation(e):
    """ Build a representation of a predpatt event tree by traversing it from
        the MAINCIT token towards the predicate.
    """

    representation = []

    maincit_node = get_maincit(e.root)
    if not maincit_node:
        return -1, representation

    # look 1 hop downward from MAINCIT
    for dep in maincit_node.dependents:
        if dep.rel in ['appos', 'nmod']:
            representation.extend(compound_text_variations(dep.dep))
    # traverse tree upward
    # NOTE: while predpatt assigns each event a root (accessible as e.root) it
    #       does NOT change the root's gov_rel to "root" or its gov to None in
    #       case the event describes a subtree of the sentence's dependency
    #       tree. A check for traversing the tree up to the root *of the event*
    #       can not be
    #           cur_node.gov
    #       but must be
    #           cur_node.__repr__() != e.root.__repr__()
    cur_node = maincit_node
    last_non_root_node_passed = None
    depth = 0
    while cur_node.__repr__() != e.root.__repr__():
        depth += 1
        representation.extend(compound_text_variations(cur_node))
        last_non_root_node_passed = cur_node.__repr__()
        cur_node = cur_node.gov
    # look 1 hop downward from root
    for dep in e.root.dependents:
        if dep.dep.__repr__() == last_non_root_node_passed:
            continue
        if dep.rel in ['nsubj', 'nsubjpass', 'dobj', 'iobj', 'nmod', 'dep']:
            representation.extend(compound_text_variations(dep.dep))
        elif dep.rel in ['csubj', 'csubjpass', 'ccomp', 'xcomp', 'advcl']:
            # dependent itself is a clause, need to do one more hop
            for ddep in dep.dep.dependents:
                if ddep.rel in ['nsubj', 'nsubjpass', 'dobj', 'iobj', 'nmod',
                                'conj', 'dep']:
                    representation.extend(compound_text_variations(ddep.dep))
    return depth, list(set(representation))


def build_fallback_representation(e):
    """ Just build compound_text_variations of all nodes tagged NOUN in the
        tree.
    """

    real_root = e.root
    while real_root.gov:
        real_root = real_root.gov

    def _collect_phrases(node):
        cur_phrss = []
        if node.tag == 'NOUN':
            cur_phrss = compound_text_variations(node)
        dep_phrss = []
        for d in node.dependents:
            if d.rel == 'punct':
                continue
            dep_phrss.extend(_collect_phrases(d.dep))
        return cur_phrss + dep_phrss
    phrases = _collect_phrases(real_root)

    return list(set(phrases))


def normalize_rep_lists(lists):
    """ Put terms in lower case
        remove non alphanumeric characters
        replace multiple whitespaces with one
    """

    def _norm(term):
        term = re.sub('[^A-Za-z0-9]', ' ', term)
        term = term.lower()
        term = re.sub('\s+', ' ', term)
        return term

    norm_lists = []
    for weight, terms in lists:
        norm_lists.append([weight, [_norm(t) for t in terms]])
    return norm_lists


def build_sentence_representation(s):
    """ Build representation of a sentence by analyzing predpatt output.

        Returns a weighted list of lists of terms.
    """

    s = merge_citation_token_lists(s)
    s = remove_qutation_marks(s)
    pp = PredPatt.from_sentence(s, cacheable=False)  # for speed tests
    raw_lists = []
    if len(pp.events) == 0:
        return []
    for e in pp.events:
        depth, rep = build_tree_representation(e)
        if len(rep) > 0:
            raw_lists.append([depth, rep])
    weight = 1
    rep_lists = []
    for rl in sorted(raw_lists, key=itemgetter(0)):
        rep_lists.append([weight, rl[1]])
        weight *= .5
    if len(rep_lists) == 0:
        fallback = build_fallback_representation(pp.events[0])
        if len(fallback) > 0:
            rep_lists = [[.25, fallback]]

    return normalize_rep_lists(rep_lists)
