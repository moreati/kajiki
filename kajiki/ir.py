from .util import gen_name

class Node(object):

    def __init__(self):
        self.filename = '<string>'
        self.lineno = 0

    def py(self): # pragma no cover
        return []

    def line(self, text):
        return PyLine(self.filename, self.lineno, text)

class TemplateNode(Node):

    def __init__(self, mod_py=None, defs=None):
        super(TemplateNode, self).__init__()
        if mod_py is None: mod_py = []
        if defs is None: defs = []
        self.mod_py = [ x for x in mod_py if x is not None ]
        self.defs = [ x for x in defs if x is not None ]

    def py(self):
        for block in self.mod_py:
            for  line in block.py():
                yield line
        yield self.line('@kajiki.Template')
        yield self.line('class template:')
        for child in self.defs:
            for line in child.py():
                yield line.indent()

class ImportNode(Node):

    def __init__(self, tpl_name, alias=None):
        super(ImportNode, self).__init__()
        self.tpl_name = tpl_name
        self.alias = alias

    def py(self):
        yield self.line(
            'local.__kj__.import_(%r, %r, globals())' % (
                self.tpl_name, self.alias))

class IncludeNode(Node):

    def __init__(self, tpl_name):
        super(IncludeNode, self).__init__()
        self.tpl_name = tpl_name

    def py(self):
        yield self.line(
            'yield local.__kj__.import_(%r, None, {}).__main__()' % (
                self.tpl_name))

class ExtendNode(Node):

    def __init__(self, tpl_name):
        super(ExtendNode, self).__init__()
        self.tpl_name = tpl_name

    def py(self):
        yield self.line(
            'yield local.__kj__.extend(%r).__main__()' % (
                self.tpl_name))

class DefNode(Node):
    prefix = '@kajiki.expose'

    def __init__(self, decl, *body):
        super(DefNode, self).__init__()
        self.decl = decl
        self.body = tuple(x for x in body if x is not None)

    def py(self):
        yield self.line(self.prefix)
        yield self.line('def %s:' % (self.decl))
        for child in optimize(self.body):
            for line in child.py():
                yield line.indent()

class InnerDefNode(DefNode):
    prefix='@__kj__.flattener.decorate'

class CallNode(Node):

    def __init__(self, caller, callee, *body):
        super(CallNode, self).__init__()
        fname = gen_name()
        self.decl = caller.replace('$caller', fname)
        self.call = callee.replace('$caller', fname)
        self.body = tuple(x for x in body if x is not None)

    def py(self):
        yield self.line('@__kj__.flattener.decorate')
        yield self.line('def %s:' % (self.decl))
        for child in optimize(self.body):
            for line in child.py():
                yield line.indent()
        yield self.line('yield ' + self.call)

class ForNode(Node):

    def __init__(self, decl, *body):
        super(ForNode, self).__init__()
        self.decl = decl
        self.body = tuple(x for x in body if x is not None)

    def py(self):
        yield self.line('for %s:' % (self.decl))
        for child in optimize(self.body):
            for line in child.py():
                yield line.indent()

class SwitchNode(Node):

    def __init__(self, decl, *body):
        super(SwitchNode, self).__init__()
        self.decl = decl
        self.body = tuple(x for x in body if x is not None)

    def py(self):
        yield self.line('local.__kj__.push_switch(%s)' % self.decl)
        for child in optimize(self.body):
            for line in child.py():
                yield line
        yield self.line('local.__kj__.pop_switch()')

class CaseNode(Node):

    def __init__(self, decl, *body):
        super(CaseNode, self).__init__()
        self.decl = decl
        self.body = tuple(x for x in body if x is not None)

    def py(self):
        yield self.line('if local.__kj__.case(%s):' % self.decl)
        for child in optimize(self.body):
            for line in child.py():
                yield line.indent()

class IfNode(Node):

    def __init__(self, decl, *body):
        super(IfNode, self).__init__()
        self.decl = decl
        self.body = tuple(x for x in body if x is not None)

    def py(self):
        yield self.line('if %s:' % self.decl)
        for child in optimize(self.body):
            for line in child.py():
                yield line.indent()

class ElseNode(Node):

    def __init__(self,  *body):
        super(ElseNode, self).__init__()
        self.body = tuple(x for x in body if x is not None)

    def py(self):
        yield self.line('else:')
        for child in optimize(self.body):
            for line in child.py():
                yield line.indent()

class TextNode(Node):

    def __init__(self, text, guard=None):
        super(TextNode, self).__init__()
        self.text = text
        self.guard = guard

    def py(self):
        s = 'yield %r' % self.text
        if self.guard:
            yield self.line('if %s: %s' % (self.guard, s))
        else:
            yield self.line(s)

class ExprNode(Node):

    def __init__(self, text):
        super(ExprNode, self).__init__()
        self.text = text

    def py(self):
        yield self.line('yield self.__kj__.escape(%s)' % self.text)

class PassNode(Node):

    def py(self):
        yield self.line('pass')

class AttrNode(Node):

    def __init__(self, attr, value, guard=None, mode='xml'):
        super(AttrNode, self).__init__()
        self.attr = attr
        self.value = value
        self.guard = guard
        self.mode = mode

    def py(self):
        x,gen = gen_name(), gen_name()
        def _body():
            yield self.line('def %s():' % gen)
            for part in self.value:
                for line in part.py():
                    yield line.indent()
            yield self.line("%s = ''.join(%s())" % (gen,gen))
            yield self.line(
                'for %s in self.__kj__.render_attrs({%r:%s}, %r):'
                % (x, self.attr, gen, self.mode))
            yield self.line('    yield %s' % x)
        if self.guard:
            yield self.line('if %s:' % self.guard)
            for l in _body():
                yield l.indent()
        else:
            for l in _body(): yield l

class AttrsNode(Node):

    def __init__(self, attrs, guard=None, mode='xml'):
        super(AttrsNode, self).__init__()
        self.attrs = attrs
        self.guard = guard
        self.mode = mode

    def py(self):
        x = gen_name()
        def _body():
            yield self.line(
                'for %s in self.__kj__.render_attrs(%s, %r):' % (x, self.attrs, self.mode))
            yield self.line('    yield %s' % x)
        if self.guard:
            yield self.line('if %s:' % self.guard)
            for l in _body():
                yield l.indent()
        else:
            for l in _body(): yield l

class PythonNode(Node):

    def __init__(self, *body):
        super(PythonNode, self).__init__()
        self.module_level = False
        blocks = []
        for b in body:
            assert isinstance(b, TextNode)
            blocks.append(b.text)
        text = ''.join(blocks)
        if text[0] == '%':
            self.module_level = True
            text = text[1:]
        self.lines = list(self._normalize(text))

    def py(self):
        for line in self.lines:
            yield self.line(line)

    def _normalize(self, text):
        if text.startswith('#\n'):
            text = text[2:]
        prefix = None
        for line in text.splitlines():
            if prefix is None:
                rest = line.lstrip()
                prefix = line[:len(line)-len(rest)]
            assert line.startswith(prefix)
            yield line[len(prefix):]

def optimize(iter_node):
    last_node = None
    for node in iter_node:
        if type(node) == TextNode:
            if (type(last_node) == TextNode
                and last_node.guard == node.guard):
                last_node.text += node.text
            else:
                if last_node is not None: yield last_node
                last_node = node
        else:
            if last_node is not None: yield last_node
            last_node = node
    if last_node is not None:
        yield last_node

class PyLine(object):

    def __init__(self, filename, lineno, text, indent=0):
        self._filename = filename
        self._lineno = lineno
        self._text = text
        self._indent = indent

    def indent(self, sz=4):
        return PyLine(self._filename, self._lineno, self._text, self._indent + sz)

    def __str__(self):
        return (' ' * self._indent) + self._text
        if self._lineno:
            return (' ' * self._indent) + self._text + '\t# %s:%d' % (self._filename, self._lineno)
        else:
            return (' ' * self._indent) + self._text
