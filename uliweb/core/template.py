#! /usr/bin/env python
#coding=utf-8

import re
import os

__templates_temp_dir = 'tmp/templates_temp'
__options = {'use_temp_dir':False}

def use_tempdir(dir=None):
    global __options, __templates_temp_dir
    
    __options['use_temp_dir'] = True
    if dir:
        __templates_temp_dir = dir
    if not os.path.exists(__templates_temp_dir):
        os.makedirs(__templates_temp_dir)

def set_options(**options):
    """
    default use_temp_dir=False
    """
    __options.update(options)

def get_temp_template(filename):
    if __options['use_temp_dir']:
        f, filename = os.path.splitdrive(filename)
        filename = filename.replace('\\', '_')
        filename = filename.replace('/', '_')
        return os.path.normcase(os.path.join(__templates_temp_dir, filename))
    return filename

def reindent(text):
    lines=text.split('\n')
    new_lines=[]
    credit=k=0
    for raw_line in lines:
        line=raw_line.strip()
        if line[:5]=='elif ' or line[:5]=='else:' or    \
            line[:7]=='except:' or line[:7]=='except ' or \
            line[:7]=='finally:':
                k=k+credit-1
        if k<0: k=0
        new_lines.append('    '*k+line)
        credit=0
        if line=='pass' or line[:5]=='pass ':
            credit=0
            k-=1
        if line=='return' or line[:7]=='return ' or \
            line=='continue' or line[:9]=='continue ' or \
            line=='break' or line[:6]=='break':
            credit=1
            k-=1
        if line[-1:]==':' or line[:3]=='if ':
            k+=1
    text='\n'.join(new_lines)
    return text

def get_templatefile(filename, dirs, default_template=None):
    if os.path.exists(filename):
        return filename
    if dirs:
        for d in dirs:
            path = os.path.join(d, filename)
            if os.path.exists(path):
                return path
    else:
        if default_template:
            return default_template

r_tag = re.compile(r'(\{\{.*?\}\})', re.DOTALL|re.M)

class Node(object):
    block = 0
    var = False
    def __init__(self, value=None):
        self.value = value
        
    def __str__(self):
        if self.value:
            return self.value
        else:
            return ''
    
class BlockNode(Node):
    def __init__(self, name=''):
        self.nodes = []
        self.vars = {}
        self.name = name
        
    def add(self, node):
        self.nodes.append(node)
        if isinstance(node, BlockNode):
            self.vars[node.name] = node
        
    def merge(self, content):
        self.nodes.extend(content.nodes)
        self.vars.update(content.vars)
        
    def clear_content(self):
        self.nodes = []
    
    def __str__(self):
        s = []
        for x in self.nodes:
            if isinstance(x, BlockNode) and x.name in self.vars:
                s.append(str(self.vars[x.name]))
            else:
                s.append(str(x))
        return ''.join(s)

class Content(BlockNode):
    def __init__(self):
        self.nodes = []
        self.vars = {}
        
class Lexer(object):
    def __init__(self, text, vars=None, env=None, dirs=None, writer='out.write'):
        self.text = text
        self.vars = vars
        self.env = env or {}
        self.dirs = dirs
        self.writer = writer
        self.content = Content()
        self.stack = [self.content]
        self.parse(text)
        
    def output(self):
        return str(self.content)
        
    def parse(self, text):
        in_tag = False
        extend = None  #if need to process extend node
        for i in r_tag.split(text):
            if i:
                if len(self.stack) == 0:
                    raise Exception, "The 'end' tag is unmatched, please check if you spell 'block' right"
                top = self.stack[-1]
                if in_tag:
                    line = i[2:-2]
                    if line and line[0] == '=':
                        name, value = '=', line[1:]
                    else:
                        v = line.strip().split(' ', 1)
                        if len(v) == 1:
                            name, value = v[0], ''
                        else:
                            name, value = v
                    if name == 'block':
                        node = BlockNode(name=value.strip())
                        top.add(node)
                        self.stack.append(node)
                    elif name == 'end':
                        self.stack.pop()
                    elif name == '=':
                        buf = "\n%s(%s)\n" % (self.writer, value)
                        top.add(buf)
                    elif name == 'include':
                        self._parse_include(value)
                    elif name == 'extend':
                        extend = value
                    else:
                        if line and in_tag:
                            top.add(line)
                else:
                    buf = "\n%s(%r, escape=False)\n" % (self.writer, i)
                    top.add(buf)
                    
            in_tag = not in_tag
        if extend:
            self._parse_extend(extend)
            
    def _parse_include(self, filename):
        filename = eval(filename, self.env, self.vars)
        fname = get_templatefile(filename, self.dirs)
        if not fname:
            raise Exception, "Can't find the template %s" % filename
        
        f = open(fname, 'rb')
        text = f.read()
        f.close()
        t = Lexer(text, self.vars, self.env, self.dirs)
        self.content.merge(t.content)
        
    def _parse_extend(self, filename):
        filename = eval(filename, self.env, self.vars)
        fname = get_templatefile(filename, self.dirs)
        if not fname:
            raise Exception, "Can't find the template %s" % filename
        
        f = open(fname, 'rb')
        text = f.read()
        f.close()
        t = Lexer(text, self.vars, self.env, self.dirs)
        self.content.clear_content()
        t.content.merge(self.content)
        self.content = t.content
            
def render_text(text, vars=None, env=None, dirs=None, default_template=None):
    dirs = dirs or ['.']
    content = Lexer(text, vars, env, dirs)
    return reindent(content.output())

def render_file(filename, vars=None, env=None, dirs=None, default_template=None, use_temp=False):
    fname = get_templatefile(filename, dirs, default_template)
    if not fname:
        raise Exception, "Can't find the template %s" % filename
    if use_temp:
        f = get_temp_template(fname)
        if os.path.exists(f):
            #todo add var judgement to test exclude variables
            if os.path.getmtime(f) >= os.path.getmtime(fname):
                return fname, file(f, 'rb').read()
    text = render_text(file(fname).read(), vars, env, dirs, default_template)
    if use_temp:
        f = get_temp_template(fname)
        try:
            fo = file(f, 'wb')
            fo.write(text)
            fo.close()
        except:
            pass
    return fname, text

def template_file(filename, vars=None, env=None, dirs=None, default_template=None):
    vars = vars or {}
    env = env or {}
    fname, code = render_file(filename, vars, env, dirs, default_template, use_temp=__options['use_temp_dir'])
    return _run(code, vars, env, fname)

def template(text, vars=None, env=None, dirs=None, default_template=None):
    vars = vars or {}
    env = env or {}
    code = render_text(text, vars, env, dirs, default_template)
    return _run(code, vars, env)

import StringIO
import cgi

class Out(object):
    encoding = 'utf-8'
    
    def __init__(self):
        self.buf = StringIO.StringIO()
        
    def _str(self, text):
        if isinstance(text, unicode):
            return text.encode(self.encoding)
        else:
            return text

    def write(self, text, escape=True):
        if escape:
            self.buf.write(self.xmlescape(text))
        else:
            self.buf.write(self._str(text))
            
    def noescape(self, text):
        self.write(self._str(text), escape=False)
        
    def json(self, text):
        from datawrap import dumps
        self.write(dumps(text))

    def xmlescape(self, data, quote=False):
        try:
            data = data.xml()
        except AttributeError:
            if not isinstance(data, (str, unicode)):
                data = str(data)
            if isinstance(data, unicode):
                data = data.encode("utf8","xmlcharrefreplace")
            data = cgi.escape(data, quote)
        return data

    def getvalue(self):
        return self.buf.getvalue()

def _prepare_run(locals, env, out):
    e = {}
    e.update(env)
    e.update(locals)
    e['out'] = out
    e['xml'] = out.noescape
    return e
    
def _run(code, locals={}, env={}, filename='template'):
    out = Out()
    e = _prepare_run(locals, env, out)
    
    if isinstance(code, (str, unicode)):
        code = compile(code, filename, 'exec')
    exec code in e
    return out.getvalue()

if __name__ == '__main__':
    print template("Hello, {{=name}}", {'name':'uliweb'})
#    print template_file('index.html', {'name':'limodou'})
#    print render_file('index.html', {'name':'limodou'})[1]
#    print render_text(a)
#    print template(a, {'abc':'limodou'})
#    def f():
#        template_file('index.html', {'name':'limodou'})
#        
#    from timeit import Timer
#    t = Timer("f()", "from __main__ import f")
#    print t.timeit(5000)
    
