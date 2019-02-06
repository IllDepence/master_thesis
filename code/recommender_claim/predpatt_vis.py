import pydot
import zlib
from predpatt import PredPatt

def recursive_follow_deps(graph, n):
    for d in n.dependents:
        if d.rel == 'punct':
            continue
        dep_id = d.dep.__repr__()
        dep_label = d.dep.text
        gov_id = d.gov.__repr__()
        gov_label = d.gov.text
        graph.add_node(pydot.Node(gov_id, label=gov_label))
        graph.add_node(pydot.Node(dep_id, label=dep_label))
        graph.add_edge(pydot.Edge(gov_id, dep_id, label=d.rel))
        recursive_follow_deps(graph, d.dep)

def pp_event_tree(e):
    graph = pydot.Dot(graph_type='graph')
    root = e.root
    graph.add_node(pydot.Node(root.__repr__(), label=root.text))
    recursive_follow_deps(graph, root)
    return graph

def predpatt_visualize(s):
    sid = '{:x}'.format(zlib.adler32(s.encode()))
    pp = PredPatt.from_sentence(s)
    for i, e in enumerate(pp.events):
        tree = pp_event_tree(e)
        tree.add_node(pydot.Node('label', label=s, shape='plaintext'))
        tree.add_edge(pydot.Edge('label', e.root.__repr__(), style='invis'))
        try:
            tree.write_png('tree_{}_{}.png'.format(sid, i))
        except:
            print(s)
            pass  # pydot errors are useless

sentences = []
sentences.append('Huedo et al. MAINCIT also describe a framework, called Gridway, for adaptive execution of applications in Grids.')
sentences.append('In “composite quantization" (CQ) MAINCIT , the overhead caused at search time by the non-orthogonality of codebooks is alleviated by learning codebooks that ensure FORMULA .')
sentences.append('The idea of SVM is based on structural risk minimization ( MAINCIT ).')
sentences.append('TABLE TABLE This Work In this work we examine an alternative approach for reducing the costs of private learning, inspired by the (non-private) models of semi-supervised learning MAINCIT and active learning CIT .')
sentences.append('This is related to the novelty detection problem and single-class support vector machine studied in statistical learning theory CIT , MAINCIT , CIT .')
sentences.append('Beyond the correlation filter based method, extensive tracking approaches were proposed and achieved state-of-the-art performance, such as structural learning CIT , CIT , CIT , sparse and low-rank learning CIT , CIT , CIT , CIT , subspace learning CIT , CIT , CIT , and deep learning CIT , MAINCIT .')
sentences.append('The usual solutions of this problem are based on using hybrid recommender techniques (see Section REF ) combining content and collaborative data MAINCIT , CIT and sometimes they are accompanied by asking for some base information (such as age, location and preferred genres) from the users.')
sentences.append('The upgraded ground-based interferometric gravitational-wave (GW) detectors LIGO CIT , CIT and Virgo CIT will begin scientific observations in mid 2015, and are expected to reach design sensitivity by 2019 MAINCIT .')
sentences.append('In contrast, the average annotation time for data-annotation methods such as CIT , MAINCIT , CIT are significantly below 0.5 FPS.')
sentences.append('MAINCIT released ChestX-ray-14, an order of magnitude larger than previous datasets of its kind, and also benchmarked different convolutional neural network architectures pre-trained on ImageNet.')
sentences.append('Object Recognition and Segmentation: The availability of large-scale, publicly available datasets such as ImageNet ( CIT ), PASCAL VOC ( CIT ), Microsoft COCO ( CIT ), Cityscapes ( MAINCIT ) and TorontoCity ( CIT ) have had a major impact on the success of deep learning in object classification, detection, and semantic segmentation tasks.')
sentences.append('Various explanations have been given for this phenomenon, e.g. senses of fairness MAINCIT , reciprocity among agents CIT , or spite and altruism CIT , CIT .')
sentences.append('Spatial Scale Selection Several automatic spatial scale selection methods have been proposed for 3D object retrieval MAINCIT .')
sentences.append('The main result in MAINCIT shows that, for every perfect codimension FORMULA ideal FORMULA in the regular local ring FORMULA with FORMULA and FORMULA we have FORMULA.')
sentences.append('The Drazin spectrum is defined by FORMULA The concept of Drazin invertible operators has been generalized by Koliha MAINCIT .')
sentences.append('Lemma 1.2 ( MAINCIT ) Let FORMULA and assume that FORMULA .')
sentences.append('FIGURE Bayesian decision theory Loss and risk In Bayesian decision theory a set FORMULA of possible actions FORMULA is considered, together with a function FORMULA describing the loss FORMULA suffered in situation FORMULA if FORMULA appears and action FORMULA is selected CIT , CIT , MAINCIT , CIT .')

for s in sentences:
    predpatt_visualize(s)
