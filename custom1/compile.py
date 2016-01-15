#!/usr/bin/env python
import argparse
import sys, os, re
import yaml
import codecs

yamlPattern = re.compile(r'\---[\n\s]*((?:\s|\S)*)[\n\s*]---', flags=re.DOTALL|re.MULTILINE)
regionStartPattern = re.compile(r'\s*#\s*region\s+(\S+)\s*{')
regionEndPattern = re.compile(r'\s*}')
interpolatePattern = re.compile(r'\{\s*(\S+)\s*\}')
indentPattern = re.compile(r'^(\s*)')

def find_comments(source):
    in_string = False
    in_s_comment = False
    in_m_comment = False
    comment = ''
    lineno = 0

    for idx in xrange(len(source)):
        if source[idx] == '\n':
            lineno += 1

        if in_s_comment:
            if source[idx] == '\n':
                in_s_comment = False
                yield dict(
                    source=comment,
                    firstchar=idx - len(comment) - 2,
                    lastchar=idx,
                    lineno=lineno)
        elif in_m_comment:
            if source[idx] == '*' and source[idx + 1] == '/':
                in_m_comment = False
                yield dict(
                    source=comment,
                    firstchar=idx - len(comment) - 2,
                    lastchar=idx + 2,
                    lineno=lineno)
        elif in_string:
            if source[idx] == in_string:
                in_string = False
            continue

        if in_m_comment or in_s_comment:
            comment += source[idx]
            continue

        in_m_comment = source[idx - 1] == '/' and source[idx] == '*'
        in_s_comment = source[idx - 1] == '/' and source[idx] == '/'

        if in_m_comment or in_s_comment:
            comment = ''
        elif source[idx] == '\'' or source[idx] == '"':
            in_string = source[idx]

def read_case(source):
    case = dict(meta=None, regions=dict())
    region_name = None
    region_start = 0
    lines = source.split('\n')

    for comment in find_comments(source):
        match = yamlPattern.match(comment['source'])
        if match:
            case['meta'] = yaml.safe_load(match.group(1))
            continue

        match = regionStartPattern.match(comment['source'])
        if match:
            region_name = match.group(1)
            region_start = comment['lineno']
            continue

        if region_name:
            match = regionEndPattern.match(comment['source'])
            if match:
                case['regions'][region_name] = \
                    '\n'.join(lines[region_start:comment['lineno'] - 1])
                region_name = None
                region_start = 0

    return case

def expand_regions(source, context):
    replacements = []
    lines = source.split('\n')

    for comment in find_comments(source):
        match = yamlPattern.match(comment['source'])
        if match:
            replacements.insert(0, dict(value='', **comment))
            continue

        match = interpolatePattern.match(comment['source'])

        if match == None:
            continue
        value = context['regions'].get(match.group(1), '')
        replacements.insert(0, dict(value=value, **comment))

    for replacement in replacements:
        whitespace = indentPattern.match(lines[replacement['lineno']]).group(1)
        source = source[:replacement['firstchar']] + \
            indent(replacement['value'], whitespace).lstrip() + \
            source[replacement['lastchar']:]
    setup = context['regions'].get('setup')

    if setup:
        source = setup + '\n' + source

    return source

def indent(text, prefix = '    '):
    if isinstance(text, list):
        lines = text
    else:
        lines = text.split('\n')

    return prefix + ('\n' + prefix).join(lines)

def frontmatter(case_values, form_values, sources):
    sources = indent(sources, '// - ')
    description = case_values['meta']['desc'] + \
        ' (' + form_values['meta']['name'] + ')'
    lines = []

    lines += [
        '// This file was procedurally generated from the following sources:',
        sources,
        '/*---',
        'description: ' + description,
        'es6id: ' + form_values['meta']['es6id']
    ]

    if case_values['meta'].get('features'):
        lines += ['features: ' + yaml.dump(case_values['meta'].get('features'))]

    if case_values['meta'].get('negative'):
        lines += ['negative: ' + case_values['meta'].get('negative')]

    lines += [
        'info: >',
        indent(case_values['meta']['info']),
        '',
        indent(form_values['meta']['info']),
        '---*/'
    ]

    return '\n'.join(lines)

def is_template_file(filename):
  return re.match('^[^\.].*\.hashes', filename)

def forms(directory):
    file_names = map(
        lambda x: directory + '/' + x,
        filter(is_template_file, os.listdir(directory))
    )

    for file_name in file_names:
        with open(file_name) as template_file:
            yield (file_name, template_file.read())

def tests(directory):
    for subdirectory, _, file_names in os.walk(directory):
        file_names = map(
            lambda x: os.path.join(subdirectory, x),
            filter(is_template_file, file_names)
        )

        for file_name in file_names:
            yield file_name

def expand(filename):
    case_values = None
    output = []

    with open(filename) as handle:
        case_values = read_case(handle.read())

    form_location = os.path.join('src', 'forms', case_values['meta']['template'])

    for form_filename, form_source in forms(form_location):
        form_values = read_case(form_source)
        output.append(dict(
            name = form_values['meta']['path'] + os.path.basename(filename[:-7]) + '.js',
            source = frontmatter(case_values, form_values, [filename, form_filename]) + '\n' + expand_regions(form_source, case_values)
        ))

    return output

def print_test(test):
    print '/**'
    print ' * ----------------------------------------------------------------'
    print ' * ' + test['name']
    print ' * ----------------------------------------------------------------'
    print ' */'
    print test['source']
    print '\n'

def write_test(prefix, test):
    location = os.path.join(prefix, test['name'])
    path = os.path.dirname(location)
    if not os.path.exists(path):
        os.makedirs(path)
    with codecs.open(location, 'w', 'utf-8') as handle:
        handle.write(test['source'])

parser = argparse.ArgumentParser(description="foobar")
parser.add_argument('-o', '--out', help='''The directory to write the
    compiled tests. If unspecified, tests will be written to standard out.''')
parser.add_argument('cases', help='''Test cases to generate. May be a file or a
    directory.''')
args = parser.parse_args()

if os.path.isdir(args.cases):
    cases = tests(args.cases)
else:
    cases = [args.cases]

for case in cases:
    for test in expand(case):
        if args.out:
            write_test(args.out, test)
        else:
            print_test(test)
