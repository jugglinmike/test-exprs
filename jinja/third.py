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
        print(body)

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

        name = parser.parse_expression()

        body = parser.parse_statements(['name:endcase'], drop_needle=True)
        body.append(nodes.TemplateData('\n\n'))

        return body

env = jinja2.Environment(
    optimized=False,
    extensions=[InsertExtension, RegionExtension, CaseExtension],
    block_start_string='/*#',
    block_end_string='*/',
    line_statement_prefix='//#')
tmpl = env.from_string('''
//# region elems
[x = 23]
//#- endregion

//# region vals
[,]
//#- endregion

//# region body
assert.sameValue(x, 23);
//# endregion

//# case var
var /*# insert elems */ = /*# insert vals */;
//# insert body
//# endcase

//# case funcexpr
var callCount = 0;
var f = function(/*# insert elems */) {
  //# insert body
  callCount = callCount + 1;
};
f(/*# insert vals */);
assert.sameValue(callCount, 1);
//# endcase

//# case genmeth
var callCount = 0;
var obj = {
  *method(/*# insert elems */) {
    //# insert body
    callCount = callCount + 1;
  }
};
obj.method().next(/*# insert vals */);
assert.sameValue(callCount, 1);
//# endcase
''')

print tmpl.render(name='Mark')
