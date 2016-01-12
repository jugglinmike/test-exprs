import sys, os, re
import jinja2
from jinja2 import nodes
from jinja2.ext import Extension

class SingleLineExtension(Extension):
    """Replace single-line delimiters with multi-line delimiters. Although
    Jinja supports configuring token sequences for single-line blocks,
    any whitespace preceeding such blocks is trimmed, making it inappropriate
    for use here."""
    def preprocess(self, text, name, filename):
        return re.sub(r'//\s*#(.*)$', r'/*#\1 */', text, flags=re.MULTILINE)

class RegionExtension(Extension):
    tags = set(['region'])

    def parse(self, parser):
        lineno = next(parser.stream).lineno

        name = parser.parse_assign_target()
        body = parser.parse_statements(('name:endregion',), drop_needle=True);
        return nodes.AssignBlock(name, body, lineno=lineno)

class InsertExtension(Extension):
    tags = set(['insert'])

    def parse(self, parser):
        next(parser.stream)

        name = parser.parse_expression()

        return self.environment.regions[name.name]

class SetValueExtension(Extension):
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

class SetStatementExtension(Extension):
    def parse(self, parser):
        target = next(parser.stream)
        end_expr = 'name:end' + target.value
        return nodes.AssignBlock(
            nodes.Name(target.value, 'store'),
            parser.parse_statements((end_expr,), drop_needle=True),
            lineno=target.lineno)

class TemplateExtension(SetValueExtension):
    tags = set(['template', 'desc', 'path', 'name', 'es6id'])

class Template2Extension(SetStatementExtension):
    tags = set(['info'])

env = jinja2.Environment(
    optimized=False,
    extensions=[SingleLineExtension, TemplateExtension, Template2Extension, InsertExtension, RegionExtension],
    trim_blocks=True,
    block_start_string='/*#',
    block_end_string='*/')

src = ''
with open(sys.argv[1]) as l:
    src = l.read()
tmpl = env.from_string(src)

context = dict()
for x in dir(tmpl.module):
    context[x] = getattr(tmpl.module, x)

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
