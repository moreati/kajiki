import unittest

from lxml import etree 

from fastpt import Template, NS_DECL

def nospace(s):
    if isinstance(s, basestring):
        return ''.join(ch for ch in s if ch not in (' \t\r\n'))
    else:
        return nospace(etree.tostring(s))

class TestExpand(unittest.TestCase):

    def test_def(self):
        t0 = Template(text='<div %s py:def="foo(x)"/>' % NS_DECL)
        t1 = Template(text='<py:def %s function="foo(x)"><div/></py:def>' % NS_DECL)
        assert nospace(t0.expand()) == nospace(t1.expand()), \
            '%s\nis not\n%s' % (etree.tostring(t0.expand()),
                                etree.tostring(t1.expand()))
        
    def test_complex(self):
        t0 = Template(text='''<div %s>
    <ul>
        <li py:for="i,line in enumerate(lines)" py:if="i %% 2">$i: $line</li>
    </ul>
</div>
''' % NS_DECL)
        t1 = Template(text='''<div %s>
    <ul>
        <py:for each="i, line in enumerate(lines)">
            <py:if test="i %% 2">
                <li>$i: $line</li>
            </py:if>
        </py:for>
    </ul>
</div>
''' % NS_DECL)
        assert nospace(t0.expand()) == nospace(t1.expand()), \
            '%s\nis not\n%s' % (etree.tostring(t0.expand()),
                                etree.tostring(t1.expand()))

class TestCompile(unittest.TestCase):

    def test_compile_simple(self):
        t0 = Template(text='<span>Hello there, $name! ${1+1+444}</span>')
        for line in t0.compile().py():
            print line

    def test_compile_if(self):
        t0 = Template(text='''<span %s py:if="name">
    <ul>
        <li py:for="i in range(10)"
            >Hello there, $name! ${i*i} <py:if
              test="i %% 2">Odd</py:if><py:if
              test="not i %% 2">Even</py:if
        ></li>
    </ul>
</span>
''' % NS_DECL)
        t0.compile()
        print t0._text
        print t0.render(name='Rick')