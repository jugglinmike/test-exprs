import jinja2

env = jinja2.Environment(line_statement_prefix='// #')
tmpl = env.from_string('''
Hello, world!
// # print name
''')

print tmpl.render(name='Mark')
