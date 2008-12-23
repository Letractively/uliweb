#! /usr/bin/env python
#coding=utf-8
# This module is used to parse and create new style ini file. This
# new style ini file format should like a very simple python program
# but you can define section like normal ini file, for example:
#
#    [default]
#    key = value
#
# Then the result should be ini.default.key1 = value1
# Whole ini file will be parsed into a dict-like object, but you can access
# each section and key with '.', just like ini.section.key
# For value can be simple python data type, such as: tuple, list, dict, int
# float, string, etc. So it's very like a normal python file, but it's has
# some sections definition.

import sys
import re
import codecs
import StringIO
import locale
import copy
import tokenize
import token
try:
    import set
except:
    from sets import Set as set

try:
    defaultencoding = locale.getdefaultlocale()[1]
except:
    defaultencoding = None

if not defaultencoding:
    defaultencoding = 'UTF-8'
try:
    codecs.lookup(defaultencoding)
except:
    defaultencoding = 'UTF-8'


r_encoding = re.compile(r'\s*coding\s*[=:]\s*([-\w.]+)')

def _uni_prt(a, encoding, beautiful=False, indent=0):
    escapechars = [("\\", "\\\\"), ("'", r"\'"), ('\"', r'\"'), ('\b', r'\b'),
        ('\t', r"\t"), ('\r', r"\r"), ('\n', r"\n")]
    s = []
    indent_char = ' '*4
    if isinstance(a, (list, tuple)):
        if isinstance(a, list):
            s.append(indent_char*indent + '[')
        else:
            s.append(indent_char*indent + '(')
        if beautiful:
            s.append('\n')
        for i, k in enumerate(a):
            if beautiful:
                ind = indent + 1
            else:
                ind = indent
            s.append(indent_char*ind + _uni_prt(k, encoding, beautiful, indent+1))
            if i<len(a)-1:
                if beautiful:
                    s.append(',\n')
                else:
                    s.append(', ')
        if beautiful:
            s.append('\n')
        if isinstance(a, list):
            s.append(indent_char*indent + ']')
        else:
            if len(a) > 0:
                s.append(',')
            s.append(indent_char*indent + ')')
    elif isinstance(a, dict):
        s.append(indent_char*indent + '{')
        if beautiful:
            s.append('\n')
        for i, k in enumerate(a.items()):
            key, value = k
            if beautiful:
                ind = indent + 1
            else:
                ind = indent
            s.append('%s: %s' % (indent_char*ind + _uni_prt(key, encoding, beautiful, indent+1), _uni_prt(value, encoding, beautiful, indent+1)))
            if i<len(a.items())-1:
                if beautiful:
                    s.append(',\n')
                else:
                    s.append(', ')
        if beautiful:
            s.append('\n')
        s.append(indent_char*indent + '}')
    elif isinstance(a, str):
        t = a
        for i in escapechars:
            t = t.replace(i[0], i[1])
        s.append("'%s'" % t)
    elif isinstance(a, unicode):
        t = a
        for i in escapechars:
            t = t.replace(i[0], i[1])
        try:
            s.append("u'%s'" % t.encode(encoding))
        except:
            import traceback
            traceback.print_exc()
    else:
        s.append(str(a))
    return ''.join(s)

class Storage(dict):
    def __getattr__(self, key): 
        try: return self[key]
        except KeyError, k: return None
    def __setattr__(self, key, value): 
        self[key] = value
    def __delattr__(self, key):
        try: del self[key]
        except KeyError, k: raise AttributeError, k

class Section(Storage):
    def __init__(self, name, comments=None, encoding=None):
        self.name = name
        if comments:
            self.comments = copy.copy(comments)
        else:
            self.comments = []
        self.__fields = []
        self.__field_comments = {}
        self.encoding = encoding
            
    def add(self, name, value, comments=None):
        if not name in self:
            self.__fields.append(name)
        v = self.get(name, None)
        if isinstance(v, (list, dict)):
            if isinstance(v, list):
                value = list(set(v + value))
            else:
                value = v.update(value)
            
        self[name] = value
        if not comments:
            comments = []
        
        self.__field_comments[name] = copy.copy(comments)
        
    def dumps(self, out):
        if self.comments:
            print >> out, '\n'.join(self.comments)
        print >> out, '[%s]' % self.name
        for f in self.__fields:
            comments = self.__field_comments.get(f, None)
            if comments:
                print >> out, '\n'.join(comments)
            buf = f + " = " + _uni_prt(self[f], self.encoding)
            if len(buf) > 79:
                buf = f + " = " + _uni_prt(self[f], self.encoding, True)
            print >> out, buf
            
    def __delattr__(self, key):
        try: 
            del self[key]
            self.__fields.remove(key)
            del self.__field_commands[key]
        except KeyError, k: 
            raise AttributeError, k
    
    def __str__(self):     
        buf = StringIO.StringIO()
        self.dumps(buf)
        return buf.getvalue()
    
class Ini(Storage):
    def __init__(self, inifile=None, value=None, commentchar='#', encoding='utf-8'):
        self.inifile = inifile
        self.value = value
        self.commentchar = commentchar
        self.encoding = 'utf-8'
        self.sections = []
        
        if self.inifile:
            f = open(inifile, 'rb')
            self.read(f)
            f.close()
        
    def set_filename(self, filename):
        self.inifile = filename
        
    def get_filename(self):
        return self.inifile
    
    filename = property(get_filename, set_filename)
    
    def __delattr__(self, key):
        try: 
            del self[key]
            self.sections.remove(key)
        except KeyError, k: 
            raise AttributeError, k

    def read(self, fobj):
        encoding = None
        
        if isinstance(fobj, (str, unicode)):
            f = open(fobj, 'rb')
            text = f.read()
            f.close()
        else:
            text = fobj.read()
            
        text = text + '\n'
        begin = 0
        if text.startswith(codecs.BOM_UTF8):
            begin = 3
            encoding = 'UTF-8'
        elif text.startswith(codecs.BOM_UTF16):
            begin = 2
            encoding = 'UTF-16'
            
        if not encoding:
            try:
                unicode(text, 'UTF-8')
                encoding = 'UTF-8'
            except:
                encoding = defaultencoding
                
        self.encoding = encoding
        
        f = StringIO.StringIO(text)
        f.seek(begin)
        lineno = 0
        comments = []
        status = 'c'
        section = None
        while 1:
            lastpos = f.tell()
            line = f.readline()
            lineno += 1
            if not line:
                break
            line = line.strip()
            if line:
                if line.startswith(self.commentchar):
                    if lineno == 1: #first comment line
                        b = r_encoding.search(line[1:])
                        if b:
                            self.encoding = b.groups()[0]
                            continue
                    comments.append(line)
                elif line.startswith('[') and line.endswith(']'):
                    sec_name = line[1:-1].strip()
                    section = self.add(sec_name, comments)
                    comments = []
                elif '=' in line:
                    if section is None:
                        raise Exception, "No section found, please define it first in %s file" % self.filename

                    pos = line.find('=')
                    keyname = line[:pos].strip()
                    f.seek(lastpos+pos+1)
                    try:
                        value = self.__read_line(f)
                    except Exception, e:
                        import traceback
                        traceback.print_exc()
                        raise Exception, "Parsing ini file error in line(%d): %s" % (lineno, line)
                    try:
                        if ((value.startswith("u'") and value.endswith("'")) or
                            (value.startswith('u"') and value.endswith('"'))):
                            v = unicode(value[2:-1], self.encoding)
                        else:
                            v = eval(value, {}, section)
                    except Exception, e:
                        raise Exception, "Converting value (%s) error in line %d" % (value, lineno)
                    
                    section.add(keyname, v, comments)
                    comments = []
            else:
                comments.append(line)
                
    def save(self, filename=None):
        if not filename:
            filename = self.filename
        if not filename:
            filename = sys.stdout
        if isinstance(filename, (str, unicode)):
            f = open(filename, 'wb')
            need_close = True
        else:
            f = filename
            need_close = False
        
        print >> f, '#coding=%s' % self.encoding
        for s in self.sections:
            section = self[s]
            section.dumps(f)

    def __read_line(self, f):
        g = tokenize.generate_tokens(f.readline)
        
        buf = []
        time = 0
        while 1:
            v = g.next()
            tokentype, t, start, end, line = v
            if tokentype == 54:
                continue
            if tokentype in (token.INDENT, token.DEDENT, tokenize.COMMENT):
                continue
            if tokentype == token.NEWLINE:
                return ''.join(buf)
            else:
                if t == '=' and time == 0:
                    time += 1
                    continue
                buf.append(t)
    
    def add(self, sec_name, comments=None):
        if sec_name in self:
            section = self[sec_name]
        else:
            section = Section(sec_name, comments, self.encoding)
            self[sec_name] = section
            self.sections.append(sec_name)
        return section
    
    def __str__(self):     
        buf = StringIO.StringIO()
        self.save(buf)
        return buf.getvalue()
    
if __name__ == '__main__':
    text = """\
# coding = utf8

#comment of default section
[default]
key1 = 'value'
key2 = 1

#key3 comment
key3 = (1,2,3)

key4+ = (
'a', 'b', 'c'
)
key5 = {
'a':1,
'b':2
}
key6 = u'中\\n文'
"""
    f = StringIO.StringIO(text)
    x = Ini()
    x.read(f)
    print '--------------------------'
    print repr(x)
    print '--------------------------'
    print x
    print x.default.key1, x.default.key2