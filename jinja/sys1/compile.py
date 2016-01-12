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
    tags = set(['template', 'desc', 'path', 'name', 'es6id', 'negative'])

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


frontmatter = """/*---
description: /*{ desc }*/ (/*{ case.name }*/)
es6id: /*{ case.es6id }*/
//# if negative
negative: /*{ negative }*/
//# endif
info: >
    /*{ case.info | indent }*/
    /*{ info | indent }*/
---*/
"""

def templates(directory):
    file_names = map(
        lambda x: directory + '/' + x,
        filter(
            lambda x: re.match('^[^\.].*\.hashes', x),
            os.listdir(directory)
            )
        )
    for file_name in file_names:
        with open(file_name) as template_file:
            yield template_file.read()

def expand(filename):
    env = Test262Env()
    context = None
    output = []

    with open(filename) as handle:
        context = env.from_string(handle.read()).module.__dict__

    for case_source in templates('templates/' + context['template']):
        case_values = env.from_string(case_source).module
        template = env.from_string(frontmatter + case_source)
        output.append(dict(
            name = case_values.path + os.path.basename(filename[:-7]) + '.js',
            source = template.render(case=case_values, **context)
        ))

    return output

def print_test(test):
    print test['name']
    print test['source']
    print '\n\n\n'

def write_test(prefix, test):
    location = prefix + '/' + test['name']
    path = os.path.dirname(location)
    if not os.path.exists(path):
        os.makedirs(path)
    with open(location, 'w') as handle:
        handle.write(test['source'])

for test in expand(sys.argv[1]):
    print_test(test)
    #write_test('tmp', test)
