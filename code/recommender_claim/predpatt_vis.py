import pydot
import re
import sys
import zlib
import numpy as np
from operator import itemgetter
from predpatt import PredPatt

MAINCITS_PATT = re.compile(r'((CIT , )*MAINCIT( , CIT)*)')
CITS_PATT = re.compile(r'(((?<!MAIN)CIT , )*(?<!MAIN)CIT( , (?<!MAIN)CIT)*)')
TOKEN_PATT = re.compile(r'(MAINCIT|CIT|FORMULA|REF|TABLE|FIGURE)')
QUOTMRK_PATT = re.compile(r'[“”„"«»‹›《》〈〉]')

CITS_TOKEN_PATT = re.compile(r'(MAIN)?CIT( , (MAIN)?CIT)+')
CIT_TOKEN_PATT = re.compile(r'((MAIN)?CIT|((MAIN)?CIT)?( , (MAIN)?CIT))')


def recursive_follow_deps(graph, n):
    for d in n.dependents:
        if d.rel == 'punct':
            continue
        dep_id = d.dep.__repr__()
        dep_label = compound_text_variations(d.dep)[-1]
        if is_example_for(d.dep):
            ex = is_example_for(d.dep)
            ex_label = compound_text_variations(ex)[-1]
            dep_label = '{} ({})'.format(dep_label, ex_label)
        # dep_label = d.dep.text
        gov_id = d.gov.__repr__()
        graph.add_node(pydot.Node(dep_id, label=dep_label))
        graph.add_edge(pydot.Edge(gov_id, dep_id, label=d.rel))
        recursive_follow_deps(graph, d.dep)


def merge_citation_token_lists(s):
    s = MAINCITS_PATT.sub('MAINCIT', s)
    s = CITS_PATT.sub('CIT', s)
    return s


def remove_qutation_marks(s):
    return QUOTMRK_PATT.sub('', s)


def pp_dot_tree(e):
    graph = pydot.Dot(graph_type='graph')
    root = e.root
    graph.add_node(pydot.Node(root.__repr__(), label=root.text))
    recursive_follow_deps(graph, root)
    return graph


def average_out_degree(e):
    """ Calculate the average out degree of nodes, not counting leaves as 0.
    """
    def _out_degree_list(node):
        deg = 0
        child_degs = []
        for d in node.dependents:
            if d.rel == 'punct':
                continue
            deg += 1
            child_degs.extend(_out_degree_list(d.dep))
        return [deg] + child_degs
    degrees = [d for d in _out_degree_list(e.root) if d != 0]
    if len(degrees) == 0:
        degrees = [0]
    return np.mean(degrees)


def contains_maincit(node):
    """ Traverse a PredPatt event tree and return whether or not it contains a
        MAINCIT node or not.
    """

    mc = False
    for d in node.dependents:
        mc = mc or (d.gov.text == 'MAINCIT')
        mc = mc or (d.dep.text == 'MAINCIT')
        if mc:
            break
        mc = mc or contains_maincit(d.dep)
    return mc


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

    texts = []
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
    # return texts
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


def build_fallback_representation(s):
    """ Just build compound_text_variations of all nouns in the tree.
    """

    # TODO

    return None


def build_sentence_representation(s):
    """ Build representation of a sentence by analyzing predpatt output.

        Returns a weighted list of lists of terms.
    """

    s = merge_citation_token_lists(s)
    s = remove_qutation_marks(s)
    pp = PredPatt.from_sentence(s)
    raw_lists = []
    for e in pp.events:
        depth, rep = build_tree_representation(e)
        if len(rep) > 0:
            raw_lists.append([depth, rep])
    weight = 1
    rep_lists = []
    for rl in sorted(raw_lists, key=itemgetter(0)):
        rep_lists.append([weight, rl[1]])
        weight *= .5

    return rep_lists


def citation_relations(e):
    """ Return list of relations through which citations are connected to the
        rest of the sentence.

        Explicit non-integral citations are distinguishable by punct rels.
        Distinction integral / non-intergal seems non obvious on first look.
    """
    def _rels(node):
        rels = []
        for d in node.dependents:
            rels.extend(_rels(d.dep))
            if CIT_TOKEN_PATT.fullmatch(d.gov.text):
                rels.extend([d.rel])
            if CIT_TOKEN_PATT.fullmatch(d.dep.text):
                rels.extend([d.rel])
        return rels

    return _rels(e.root)


def predpatt_visualize(s):
    sid = '{:x}'.format(zlib.adler32(s.encode()))
    pp = PredPatt.from_sentence(s)
    for i, e in enumerate(pp.events):
        tree = pp_dot_tree(e)
        tree.add_node(pydot.Node('label', label=s, shape='plaintext'))
        tree.add_edge(pydot.Edge('label', e.root.__repr__(), style='invis'))
        try:
            tree.write_png('tree_{}_{}.png'.format(sid, i))
        except AssertionError:
            print('AssertionError for: {}'.format(s))
            pass  # pydot errors are useless


sentences = []
sentences.append('Huedo et al. MAINCIT also describe a framework, called Gridway, for adaptive execution of applications in Grids.')
sentences.append('In “composite quantization" (CQ) MAINCIT , the overhead caused at search time by the non-orthogonality of codebooks is alleviated by learning codebooks that ensure FORMULA .')
sentences.append('TABLE TABLE This Work In this work we examine an alternative approach for reducing the costs of private learning, inspired by the (non-private) models of semi-supervised learning MAINCIT and active learning CIT .')
sentences.append('This is related to the novelty detection problem and single-class support vector machine studied in statistical learning theory CIT , MAINCIT , CIT .')
sentences.append('The usual solutions of this problem are based on using hybrid recommender techniques (see Section REF ) combining content and collaborative data MAINCIT , CIT and sometimes they are accompanied by asking for some base information (such as age, location and preferred genres) from the users.')
sentences.append('The upgraded ground-based interferometric gravitational-wave (GW) detectors LIGO CIT , CIT and Virgo CIT will begin scientific observations in mid 2015, and are expected to reach design sensitivity by 2019 MAINCIT .')
sentences.append('In contrast, the average annotation time for data-annotation methods such as CIT , MAINCIT , CIT are significantly below 0.5 FPS.')
sentences.append('MAINCIT released ChestX-ray-14, an order of magnitude larger than previous datasets of its kind, and also benchmarked different convolutional neural network architectures pre-trained on ImageNet.')
sentences.append('Various explanations have been given for this phenomenon, e.g. senses of fairness MAINCIT , reciprocity among agents CIT , or spite and altruism CIT , CIT .')
sentences.append('Spatial Scale Selection Several automatic spatial scale selection methods have been proposed for 3D object retrieval MAINCIT .')
sentences.append('The main result in MAINCIT shows that, for every perfect codimension FORMULA ideal FORMULA in the regular local ring FORMULA with FORMULA and FORMULA we have FORMULA.')
sentences.append('The Drazin spectrum is defined by FORMULA The concept of Drazin invertible operators has been generalized by Koliha MAINCIT .')
sentences.append('Lemma 1.2 ( MAINCIT ) Let FORMULA and assume that FORMULA .')
sentences.append('FIGURE Bayesian decision theory Loss and risk In Bayesian decision theory a set FORMULA of possible actions FORMULA is considered, together with a function FORMULA describing the loss FORMULA suffered in situation FORMULA if FORMULA appears and action FORMULA is selected CIT , CIT , MAINCIT , CIT .')
sentences.append('Object Recognition and Segmentation: The availability of large-scale, publicly available datasets such as ImageNet ( CIT ), PASCAL VOC ( CIT ), Microsoft COCO ( CIT ), Cityscapes ( MAINCIT ) and TorontoCity ( CIT ) have had a major impact on the success of deep learning in object classification, detection, and semantic segmentation tasks.')
sentences.append('Beyond the correlation filter based method, extensive tracking approaches were proposed and achieved state-of-the-art performance, such as structural learning CIT , CIT , CIT , sparse and low-rank learning CIT , CIT , CIT , CIT , subspace learning CIT , CIT , CIT , and deep learning CIT , MAINCIT .')
sentences.append('The idea of SVM is based on structural risk minimization ( MAINCIT ).')

for s in sentences:
    print(build_sentence_representation(s))
    input()
    print()
    print('- - - - - - -')
    print()
    # predpatt_visualize(s)
    # print(s)
    # pp = PredPatt.from_sentence(s)
    # for e in pp.events:
    #     print('  > {}'.format(citation_relations(e)))
