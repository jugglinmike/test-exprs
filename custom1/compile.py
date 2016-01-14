import sys, os, re
import yaml

yamlPattern = re.compile(r'\---((?:\s|\S)*)\---', flags=re.DOTALL|re.MULTILINE)
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
        indent = indentPattern.match(lines[replacement['lineno']])
        source = source[:replacement['firstchar']] + \
            ('\n' + indent.group(1)).join(replacement['value'].split('\n')) + \
            source[replacement['lastchar']:]
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

    for form_filename, form_source in forms('templates/' + case_values['meta']['template']):
        form_values = read_case(form_source)
        output.append(dict(
            name = form_values['meta']['path'] + os.path.basename(filename[:-7]) + '.js',
            source = frontmatter(case_values, form_values, [filename, form_filename]) + expand_regions(form_source, case_values)
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

# TODO: Improve naming
if os.path.isdir(sys.argv[1]):
    x = tests(sys.argv[1])
else:
    x = [sys.argv[1]]

for y in x:
    for test in expand(y):
        print_test(test)
        #write_test('tmp', test)
