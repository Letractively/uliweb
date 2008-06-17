##################################################################################
#  Author: limodou
#  This file modified from web2py tmplate.py(which is part of web2py Web Framework,
#  and the author is Massimo Di Pierro <mdipierro@cs.depaul.edu>)
#  License: GPL v2
##################################################################################

import re
import os

__all__=['template']

re_write=re.compile('\{\{=(?P<value>.*?)\}\}',re.DOTALL)
re_html=re.compile('\}\}.*?\{\{',re.DOTALL)
#re_strings=re.compile('((?:""").*?(?:"""))|'+"((?:''').*?(?:'''))"+'((?:""").*?(?:"""))|'+"((?:''').*?(?:'''))"

PY_STRING_LITERAL_RE= r'(?P<name>'+ \
  r"[uU]?[rR]?(?:'''(?:[^']|'{1,2}(?!'))*''')|" +\
              r"(?:'(?:[^'\\]|\\.)*')|" +\
            r'(?:"""(?:[^"]|"{1,2}(?!"))*""")|'+ \
              r'(?:"(?:[^"\\]|\\.)*"))'
re_strings=re.compile(PY_STRING_LITERAL_RE,re.DOTALL)

re_include_nameless=re.compile('\{\{\s*include\s*\}\}')
re_include=re.compile('\{\{\s*include\s+(?P<name>.+?)\s*\}\}',re.DOTALL)
re_extend=re.compile('\s*\{\{\s*extend\s+(?P<name>.+?)\s*\}\}',re.DOTALL)

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

def replace(regex,text,f):
    i=0
    output=[]
    for item in regex.finditer(text):
        output.append(text[i:item.start()])
        output.append(f(item.group()))
        i=item.end()
    output.append(text[i:len(text)])
    return ''.join(output)

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

def render_text(text, vars=None, env=None, dirs=None, default_template=None):
    dirs = dirs or []

    if not isinstance(text, (str, unicode)):
        text = text.read()
    
    # check whether it extends a layout
    while 1:
        match = re_extend.search(text)
        if not match: break
        filename = eval(match.group('name'), env, vars)
        t = get_templatefile(filename, dirs, default_template)
        if not t:
            raise Exception, "Can't find the template file %s" % filename
            
        try: 
            parent = open(t, 'rb').read()
        except IOError: 
            raise Exception, 'Processing View %s error!' % filename
        text = text[0:match.start()] + re_include_nameless.sub(text[match.end():], parent)
    
    ##
    # check whether it includes subtemplates
    ##
    while 1:
        match = re_include.search(text)
        if not match: break
        filename = eval(match.group('name'), env, vars)
        t = get_templatefile(filename, dirs, default_template)
        if not t:
            raise Exception, "Can't find the template file %s" % filename
            
        try: 
            child = open(t,'rb').read()
        except IOError: 
            raise Exception, 'Processing View %s error!' % filename
        text = re_include.sub(child, text, 1)
    
    text = '}}%s{{' % re_write.sub('{{out.write(\g<value>)}}', text)
    text = replace(re_html, text, lambda x: '\nout.write(%s,escape=False)\n' % repr(x[2:-2]))
    text = replace(re_strings, text, lambda x: x.replace('\n','\\n'))
    code = reindent(text)

    return code

def render_file(filename, vars=None, env=None, dirs=None, default_template=None):
    fname = get_templatefile(filename, dirs, default_template)
    if not fname:
        raise Exception, "Can't find the template %s" % filename
    return fname, render_text(file(fname).read(), vars, env, dirs, default_template)
    
def template_file(filename, vars=None, env=None, dirs=None, default_template=None):
    vars = vars or {}
    env = env or {}
    fname, code = render_file(filename, vars, env, dirs, default_template)
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

def cycle(*elements):
    while 1:
        for j in elements:
            yield j
            
def _run(code, locals={}, env={}, filename='template'):
    locals['out'] = out = Out()
    locals['Xml'] = out.noescape
    
    def Get(name, default='', vars=locals):
        """
        name should be a variable name or function call, for example:
            
            {{=Get('title')}}
            {{=Get('get_title()')}}
            
        and name can also be a real variable object, for example:
            
            {{=Get(title)}}
        """
        if isinstance(name, (str, unicode)):
            try:
                return eval(name, env, vars)
            except NameError:
                return default
            return default
        if name:
            return name
        else:
            return default
    locals['Get'] = Get
    locals['Cycle'] = cycle
    
    if isinstance(code, (str, unicode)):
        try:
            code = compile(code, filename, 'exec')
        except:
            print 'xxxxxxxxxxxxxxxxxxxxxxxxxxxx'
            raise
    exec code in env, locals
    return out.getvalue()

def test():
    """
    
    >>> t = "hello, {{=name}}"
    >>> print template(t, {'name':'<limodou>'})
    hello, &lt;limodou&gt;
    >>> t = "{{if name:}}hello, {{=name}}{{else:}}no user{{pass}}"
    >>> print template(t, {'name':''})
    no user
    >>> print template(t, {'name':'limodou'})
    hello, limodou
    """
    
if __name__=='__main__':
#    import doctest
#    doctest.testmod()
    a = """
{{
def editfile(path,file):
    ext=os.path.splitext(file)[1]
    if ext in ['.py', '.css', '.js', '.html']: return A('edit',_href=URL(r=request,f='edit/%s/%s/%s' % (app, path, file)))
    else: return ''
    pass
def htmleditfile(path,file):
    return A('htmledit')
}}
{{title='bbbbb'}}
{{=Get('title', 'aaaaa')}}
    """
    print template(a)
