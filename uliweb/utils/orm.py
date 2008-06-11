# This module is used for wrapping geniusql to a simple ORM
# Author: limodou <limodou@gmail.com>
# 2008.06.11

import sys

sys.path.insert(0, '..')

__all__ = ['Field', 'get_connection', 'Model', 'migirate_table',
    'set_auto_bind', 'set_auto_migirate', 'Reference',
    'ReversedKeyException']

__default_connection__ = None  #global connection instance
__auto_bind__ = False
__auto_migirate__ = False
__DEBUG__ = False

import re
import geniusql
from storage import Storage
import decimal
import threading

r_spec = re.compile('(?P<spec>.*?)://(?:(?P<user>.*?):(?P<passwd>.*?)@)?(?:(?P<url>.*?)(?:\?(?P<arguments>.*))?)?$')

class ReversedKeyException(Exception):pass

def set_auto_bind(flag):
    global __auto_bind__
    __auto_bind__ = flag
    
def set_auto_migirate(flag):
    global __auto_migirate__
    __auto_migirate__ = flag
    
def set_debug(flag):
    global __DEBUG__
    __DEBUG__ = flag

def get_connection(connection='', default=True, **args):
    if default:
        global __default_connection__
        if not __default_connection__:
            __default_connection__ = DB(connection, **args)
        return __default_connection__
    else:
        db = DB(connection, **args)
        return db

def DB(connection='', **args):
    """
    A connection should be formatted like:
        provider://<user:password@>host:port/dbname<?arg1=value1&arg2=value2>
        
        <> can be optional
        
        for provider, they are: 
        
            sqlite, access, firebird, mysql, postgres, psycopg, sqlserver
        
        For sqlite:
        sqlite:///absolute/path/to/databasefile
        sqlite://relative/path/to/databasefile
        sqlite://   #in-memory database
    """
    b = r_spec.match(connection)
    if b:
        d = b.groupdict()
        if d['url']:
            if d['spec'] == 'sqlite':
                d['db'] = d['url']
                d['host'] = ''
                d['port'] = ''
            else:
                a, db = d['url'].split('/')
                d['db'] = db
                if ':' in a:
                    d['host'], d['port'] = a.split(':')
                    d['port'] = int(d['port'])
                else:
                    d['host'], d['port'] = a, ''
        else:
            d['db'] = d['url']
            d['host'] = ''
            d['port'] = ''
       
    else:
        d = {'spec':connection}
    #clear empty key
    for k, v in d.copy().items():
        if not v:
            del d[k]
            
    d.update(args)
    provider = d['spec']
    if provider == 'sqlite':
        if d.get('db', None):
            d['name'] = d['db']
        else:
            d['name'] = ':memory:'
    elif provider == 'firebird':
        if d.get('passwd', None):
            d['password'] = d['passwd']
    elif provider == 'mysql':
        d['encoding'] = d.setdefault('encoding', 'utf8')
    db = geniusql.db(provider, **d)
    if provider == 'sqlite':
        db.create()
    db._schema = db.schema()
    db._schema.create()
    
#    def log(message, self=db):
#        import logging
#        handler = logging.StreamHandler()
#        _logger = logging.getLogger('werkzeug')
#        _logger.addHandler(handler)
#        if __DEBUG__:
#            _logger.setLevel(logging.DEBUG)
#            _logger.debug(message)
#    
#    setattr(db, 'log', log)
#    
    return db

class Field(object):
    creation_counter = 0

    def __init__(self, type, max_length=None, **kwargs):
        self.type = type
        self.max_length = max_length
        self.kwargs = kwargs
            
    def create(self, schema):
        if self.max_length:
            hints = self.kwargs.setdefault('hints', {})
            if self.type is float or self.type is decimal.Decimal:
                hints['precision'] = self.max_length
                scale = self.kwargs.pop('scale', None)
                if scale:
                    hints['scale'] = scale
            else:
                hints['bytes'] = self.max_length
        self.column = schema.column(self.type, **self.kwargs)
        return self.column
    
    def __repr__(self):
        return '<Field %s %r>' % (self.name, self.type)

class Reference(Field):
    def __init__(self, tablename, ref_field='id'):
        if issubclass(tablename, Model):
            tablename = tablename.tablename
        elif isinstance(tablename, geniusql.Table):
            tablename = tablename.name
        self.tablename = tablename
        self.ref_field = ref_field

    def create(self, schema):
        self.column = schema.column(int)
        return self.column

    def __repr__(self):
        return '<Reference %s %r>' % (self.tablename, self.ref_field)
  
def is_reversed(f):
    if f in ['add_index', 'add_reference', 'bind', 'create', 'created', 
        'db', 'delete', 'delete_all', 'drop', 'drop_primary', 'fields', 
        'fields_list', 'id_clause', 'insert', 'is_existed', 'keys', 
        'rename', 'save', 'save_all', 'schema', 'select', 'select_all', 
        'set_primary', 'set_tablename', 'table', 'tablename', 'put',
        'dict', 'get', 'remove', 'filter']:
        return True
    else:
        return False
    
class ModelMetaclass(type):
    def __new__(cls, name, bases, attrs):
        fields = {}
        d = attrs.copy()
        for field_name, obj in d.items():
            if isinstance(obj, Field):
                if is_reversed(field_name):
                    raise ReversedKeyException("This word [%s] is a reversed key, "
                        "please try another name" % field_name)
                obj.name = field_name
                fields[field_name] = obj
                del attrs[field_name]

        f = {}
        for base in bases[::-1]:
            if hasattr(base, 'fields'):
                f.update(base.fields)

        f.update(fields)
        if 'id' not in f:
            f['id'] = Field(int, autoincrement=True, key=True)
            f['id'].name = 'id'
        attrs['fields'] = f
        
        for method in ['insert', 'drop', 'rename', 'add_index', 'set_primary',
            'drop_primary', 'id_clause', 'save', 'save_all', 'delete_all',
            'keys', 'select', 'select_all', 'delete']:
            def _f(cls, method=method, *args, **kwargs):
                if not hasattr(cls, 'table'):
                    cls.bind(auto_create=__auto_migirate__)
                func = getattr(cls.table, method)
                ret = func(*args, **kwargs)
                if isinstance(ret, dict):
                    ret = Storage(ret)
                return ret
            attrs[method] = classmethod(_f)
        
        fields_list = [(k, v) for k, v in fields.items()]
        fields_list.sort(lambda x, y: cmp(x[1].creation_counter, y[1].creation_counter))
        attrs['fields_list'] = fields_list
        
        obj = type.__new__(cls, name, bases, attrs)
        obj.set_tablename()
        if obj.__class__.__name__ != 'Model' and __auto_bind__:
            obj.bind(auto_create=__auto_migirate__)
        return obj
    
    def __lshift__(cls, other):
        return geniusql.Join(cls.table, cls._get_table(other), leftbiased=True)
    __rrshift__ = __lshift__
    
    def __rshift__(cls, other):
        return geniusql.Join(cls.table, cls._get_table(other), leftbiased=False)
    __rlshift__ = __rshift__
    
    def _get_table(cls, other):
        if issubclass(other, Model):
            t = other.table
        else:
            t = other
        return t
    
    def __and__(cls, other):
        return geniusql.Join(cls.table, cls._get_table(other))
    
    def __rand__(cls, other):
        return geniusql.Join(cls._get_table(other), cls.table)
   
class Model(object):

    __metaclass__ = ModelMetaclass
    
    _lock = threading.Lock()
    _c_lock = threading.Lock()
    
    def __init__(self, **kwargs):
        self.id = None
        self._old_values = {}
        for k, v in kwargs.items():
            setattr(self, k, v)
        
    def _set_saved(self):
        self._old_values = self.dict()
        
    def dict(self):
        d = {}
        for k, v in self.fields.items():
            t = getattr(self, k, None)
            if t:
                d[k] = t
        return d
            
    def _get_data(self):
        if not bool(self.id):
            return self.dict()
        else:
            d = {}
            d['id'] = self.id
            for k, v in self.fields.items():
                t = self.old_values.get(k, None)
                if repr(v) != repr(t):
                    d[k] = v
        return d
            
    def put(self):
        d = self._get_data()
        if d:
            if not bool(self.id):
                obj = self.table.insert(**d)
                self.id = obj['id']
            else:
                self.table.save(**d)
            self._set_saved()
        
    @classmethod
    def remove(cls, obj):
        cls.table.delete(** obj.dict())
    
    @classmethod
    def set_tablename(cls):
        if not hasattr(cls, '__tablename__'):
            cls.tablename = cls.__name__.lower()
        else:
            cls.tablename = cls.__tablename__
    
    @classmethod
    def bind(cls, db=None, auto_create=False, force=False):
        cls._lock.acquire()
        try:
            if not db and not __default_connection__:
                return
            if not hasattr(cls, 'created') or force:
                cls.db = db or get_connection()
                cls.schema = schema = cls.db._schema
                cls.table = table = schema.table(cls.tablename)
                for k, f in cls.fields.items():
                    table[k] = f.create(schema)
                    if isinstance(f, Reference):
                        cls.add_reference(k, f.tablename, f.ref_field)
                dict.__setitem__(schema, cls.tablename, table)
                if auto_create:
                    cls.create(migirate=True)
                table.created = True
                cls.created = True
        finally:
            cls._lock.release()
            
    @classmethod
    def is_existed(cls):
        try:
            cls.schema._get_table(cls.tablename)
            return True
        except geniusql.errors.MappingError:
            return False

    @classmethod
    def create(cls, force=False, migirate=False):
        cls._c_lock.acquire()
        try:
            f = cls.is_existed()
            if not f or (f and force):
                cls.table.create()
            if f and migirate and not force:
                migirate_table(cls.table, cls.schema)
        finally:
            cls._c_lock.release()
            
    @classmethod
    def add_reference(cls, fieldname, tablename, ref_field):
        cls.table.references[tablename] = (fieldname, tablename, ref_field)
        cls.table.add_index(fieldname)
        
    @classmethod
    def get(cls, restriction=None, **kwargs):
        obj = cls.table.select(restriction, **kwargs)
        o = cls(**obj)
        o._set_saved()
        return o
    
    @classmethod
    def filter(cls, restriction=None, order=None, limit=None, **kwargs):
        for obj in cls.table._select_lazy(restriction, order, limit, **kwargs):
            o = cls(**obj)
            o._set_saved()
            yield o
            
    def __repr__(self):
        s = []
        for k, v in self.fields_list:
            s.append('%r:%r' % (k, getattr(self, k, None)))
        return ('<%s {' % self.__class__.__name__) + ','.join(s) + '}>'
            
def migirate_table(table, schema):
    def compare_column(a, b):
        return ((a.pytype is b.pytype) and (a.dbtype.__class__.__name__ == b.dbtype.__class__.__name__)
            and (a.default == b.default) and (a.key == b.key))

    t = schema.discover(table.name)
    
    for k, v in table.items():
        if k in t:
            if not compare_column(v, t[k]):
                table[k] = v
            dict.__delitem__(t, k)
        elif not k in t:
            table._add_column(v)
    for k, v in t.items():
        del t[k]
    
if __name__ == '__main__':
    db = get_connection('sqlite')
    db.create()
    set_auto_bind(True)
    set_auto_migirate(True)
    set_debug(True)
    
    class Test(Model):
        username = Field(str)
        year = Field(int)
    
    Test.insert(username='limodou')
    Test.insert(username='xxxxxxx')
    print list(Test.filter())
    t = Test(username='zoom', year=30)
    t.put()
    print list(Test.filter())
    Test.remove(t)
    print list(Test.filter())
    t = Test.get(username='limodou')
    print t
    
#    class Test(Model):
#        username = Field(str)
#        year = Field(int)
#        age = Field(int)
#        
#    print list(Test.select_all())