import sys, os, re
import jinja2
from jinja2 import nodes
from jinja2.ext import Extension

class RegionExtension(Extension):
    tags = set(['region'])

    def __init__(self, environment):
        super(RegionExtension, self).__init__(environment)

        environment.extend(regions=dict())

    def preprocess(self, text, name, filename):
        return re.sub(r'//\s*#(.*)$', r'/*#\1 */', text, flags=re.MULTILINE)

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

class TemplateExtension(Extension):
    tags = set(['template', 'desc', 'path', 'name', 'es6id'])

    def parse(self, parser):
        target = next(parser.stream)

        value = ''
        while not parser.stream.current.test_any('block_end'):
            value += parser.stream.current.value
            parser.stream.next()

        return nodes.Assign(
            nodes.Name(target.value, 'store'),
            nodes.Const(value),
            lineno=target.lineno)

env = jinja2.Environment(
    optimized=False,
    extensions=[TemplateExtension, InsertExtension, RegionExtension],
    block_start_string='/*#',
    trim_blocks=True,
    block_end_string='*/')

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
        print 'es6id: ' + template.module.es6id
        print 'info: >'
        print '    ' + '\n    '.join(template.module.info.rstrip().split('\n'))
        print ''
        print '    ' + '\n    '.join(tmpl.module.info.rstrip().split('\n'))
        print '---*/'
        print template.render(context)
        print '\n\n\n'
