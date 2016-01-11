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

        args = [parser.parse_expression()]

        body = parser.parse_statements(['name:endcase'], drop_needle=True)

        return body

env = jinja2.Environment(
    extensions=[InsertExtension, RegionExtension, CaseExtension],
    line_statement_prefix='// #')
tmpl = env.from_string('''
Hello, world!

// # region body
This is the body
// # endregion

// # case first
first case (before)
// # insert body
first case (after)
// # endcase

// # case second
second case (before)
// # insert body
second case (after)
// # endcase
''')

print tmpl.render(name='Mark')
