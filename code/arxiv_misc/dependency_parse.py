from nltk.parse.stanford import StanfordDependencyParser

def draw_deps(r, curr_node=None, rel=None, depth=0):
    if not curr_node:
        curr_node = r.root
    indent = ' '*(depth*2)
    arrow = ''
    if rel:
        arrow = '-{}->'.format(rel)
    print('{}{}{}'.format(indent, arrow, curr_node['word']))
    for k, vs in curr_node['deps'].items():
        for v in vs:
            draw_deps(r, r.get_by_address(v), k, depth+1)

p = '/home/tarek/dl/stanford-parser-full-2018-10-17/stanford-parser.jar'
m = '/home/tarek/dl/stanford-parser-full-2018-10-17/stanford-parser-3.9.2-models.jar'
dependency_parser = StanfordDependencyParser(path_to_jar=p, path_to_models_jar=m)

rs = dependency_parser.raw_parse('To achieve this, we first note that unlike many other HDG methods for incompressible flows CIT , CIT , CIT , CIT , CIT , CIT , MAINCIT , the HDG methods of CIT and CIT contain also facet unknowns for the pressure.')
r = [r for r in rs][0]
draw_deps(r)
