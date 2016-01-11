import sys, os, re
import jinja2
from jinja2 import nodes
from jinja2.ext import Extension

class RegionExtension(Extension):
    tags = set(['region'])

    def __init__(self, environment):
        super(RegionExtension, self).__init__(environment)

        environment.extend(regions=dict())

    def parse(self, parser):
        next(parser.stream)

        name = parser.parse_expression()

        body = parser.parse_statements(['name:endregion'], drop_needle=True)

        self.environment.regions[name.name] = body

        return []

class InsertExtension(Extension):
    tags = set(['insert'])

    def parse(self, parser):
        next(parser.stream)

        name = parser.parse_expression()

        return self.environment.regions[name.name]

class CaseExtension(Extension):
    tags = set(['case'])

    def parse(self, parser):
        next(parser.stream)

        thing = ''
        while not parser.stream.current.test_any('block_end'):
            thing += parser.stream.current.value
            parser.stream.next()
        #name = parser.parse_expression()
        #print name

        body = parser.parse_statements(['name:endcase'], drop_needle=True)
        body.append(nodes.TemplateData('\n\n'))

        return body

# This is a broken mess
# TODO: Fix it
class TemplateExtension(Extension):
    tags = set(['template', 'desc'])

    def parse(self, parser):
        target = next(parser.stream)
        lineno = target.lineno
        thing = ''
        while not parser.stream.current.test_any('block_end'):
            thing += parser.stream.current.value
            parser.stream.next()
        return nodes.Assign(target, nodes.Name(thing, 'store'), lineno=lineno)

env = jinja2.Environment(
    optimized=False,
    extensions=[TemplateExtension, InsertExtension, RegionExtension, CaseExtension],
    block_start_string='/*#',
    block_end_string='*/',
    line_statement_prefix='//#')

src = ''
with open(sys.argv[1]) as l:
    src = l.read()
tmpl = env.from_string(src)
context = dict()
for x in filter(lambda x: x.startswith('region_'), dir(tmpl.module)):
    context[x[7:]] = getattr(tmpl.module, x)

template_file_names = map(
    lambda x: 'templates/' + tmpl.module.template + '/' + x,
    filter(
        lambda x: re.match('^[^\.].*\.hashes', x),
        os.listdir('templates/' + tmpl.module.template)
        )
    )

for file_name in template_file_names:
    with open(file_name) as template_src:
        template = env.from_string(template_src.read())
        test_file_name = template.module.path + '/' + sys.argv[1][6:-7] + '.js'
        print test_file_name
        print '/*---'
        print 'description: ' + tmpl.module.desc + ' (' + template.module.name + ')'
        print 'info: >'
        print '    ' + '\n    '.join(template.module.info.rstrip().split('\n'))
        print ''
        print '    ' + '\n    '.join(tmpl.module.info.rstrip().split('\n'))
        print '---*/'
        print template.render(context)
        print '\n\n\n'
