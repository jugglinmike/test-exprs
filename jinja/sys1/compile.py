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

class Test262Env(jinja2.Environment):
    def __init__(self):
        super(Test262Env, self).__init__(
            optimized=False,
            extensions=[
                SingleLineExtension, TemplateExtension, Template2Extension,
                RegionExtension
            ],
            trim_blocks=True,
            block_start_string='/*#',
            block_end_string='*/',
            variable_start_string='/*{',
            variable_end_string='}*/')

env = Test262Env()

src = ''
with open(sys.argv[1]) as l:
    src = l.read()
tmpl = env.from_string(src)

context = dict()
def is_dunder(string):
    return re.match('^__.*__$', string) != None

for x in filter(lambda x: not is_dunder(x), dir(tmpl.module)):
    context[x] = getattr(tmpl.module, x)

template_file_names = map(
    lambda x: 'templates/' + tmpl.module.template + '/' + x,
    filter(
        lambda x: re.match('^[^\.].*\.hashes', x),
        os.listdir('templates/' + tmpl.module.template)
        )
    )

frontmatter = """/*---
description: /*{ desc }*/ (/*{ case.name }*/)
es6id: /*{ case.es6id }*/
info: >
    /*{ case.info | indent }*/
    /*{ info | indent }*/
---*/"""

for file_name in template_file_names:
    with open(file_name) as template_file:
        case_source = template_file.read()
        case_values = env.from_string(case_source).module
        template = env.from_string(frontmatter + case_source)
        test_file_name = case_values.path + '/' + sys.argv[1][6:-7] + '.js'
        print test_file_name
        print template.render(case=case_values, **context)
        print '\n\n\n'
