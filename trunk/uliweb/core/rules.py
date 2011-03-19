import os
import inspect

class ReservedKeyError(Exception):pass

__exposes__ = {}
__no_need_exposed__ = []
__class_methods__ = {}
__app_rules__ = {}
__url_names__ = {}
static_views = []

reserved_keys = ['settings', 'redirect', 'application', 'request', 'response', 'error',
    'json']

def add_rule(map, url, endpoint=None, **kwargs):
    from werkzeug.routing import Rule
    kwargs['endpoint'] = endpoint
    map.add(Rule(url, **kwargs))
            
def merge_rules():
    s = []
    for v in __exposes__.itervalues():
        s.extend(v)
    return __no_need_exposed__ + s

def clear_rules():
    global __exposes__, __no_need_exposed__
    __exposes__ = {}
    __no_need_exposed__ = []

def set_app_rules(rules):
    global __app_rules__
    __app_rules__ = rules
    
def expose(rule=None, **kwargs):
    e = Expose(rule, **kwargs)
    if e.parse_level == 1:
        return rule
    else:
        return e
    
class Expose(object):
    def __init__(self, rule=None, **kwargs):
        if inspect.isfunction(rule) or inspect.isclass(rule):
            self.parse_level = 1
            self.rule = None
            self.kwargs = {}
            self.parse(rule)
        else:
            self.parse_level = 2
            self.rule = rule
            self.kwargs = kwargs
            
    def _fix_url(self, appname, rule):
        if appname in __app_rules__:
            suffix = __app_rules__[appname]
            url = rule.lstrip('/')
            return os.path.join(suffix, url).replace('\\', '/')
        else:
            return rule
            
    def _get_path(self, f):
        m = f.__module__.split('.')
        s = []
        for i in m:
            if not i.startswith('views'):
                s.append(i)
        appname = '.'.join(s)
        return appname, '/'.join(s)
    
    def parse(self, f):
        if inspect.isfunction(f) or inspect.ismethod(f):
            func, result = self.parse_function(f)
            a = __exposes__.setdefault(func, [])
            a.append(result)
        else:
            result = list(self.parse_class(f))
            __no_need_exposed__.extend(result)
            
    def parse_class(self, f):
        appname, path = self._get_path(f)
        clsname = f.__name__
        if self.rule:
            prefix = self.rule
        else:
            prefix = '/' + '/'.join([path, clsname])
        for name in dir(f):
            func = getattr(f, name)
            if (inspect.ismethod(func) or inspect.isfunction(func)) and not name.startswith('_'):
                if hasattr(func, '__exposed__') and func.__exposed__:
                    new_endpoint = '.'.join([func.__module__, f.__name__, name])
                    if func.im_func in __exposes__:
                        for v in __exposes__.pop(func.im_func):
                            if func.__no_rule__:
                                rule = self._get_url(appname, prefix, func)
                            else:
                                rule = v[2]
                            __no_need_exposed__.append((v[0], new_endpoint, rule, v[3]))
                            for k in __url_names__.iterkeys():
                                if __url_names__[k] == v[1]:
                                    __url_names__[k] = new_endpoint
                else:
                    rule = self._get_url(appname, prefix, func)
                    endpoint = '.'.join([f.__module__, clsname, func.__name__])
                    yield appname, endpoint, rule, {}
    
    def _get_url(self, appname, prefix, f):
        args = inspect.getargspec(f)[0]
        if args:
            if inspect.ismethod(f):
                args = args[1:]
            args = ['<%s>' % x for x in args]
        if f.__name__ in reserved_keys:
            raise ReservedKeyError, 'The name "%s" is a reversed key, so please change another one' % f.__name__
        prefix = prefix.rstrip('/')
        rule = self._fix_url(appname, '/'.join([prefix, f.__name__] +args))
        return rule
    
    def parse_function(self, f):
        args = inspect.getargspec(f)[0]
        if args:
            args = ['<%s>' % x for x in args]
        if f.__name__ in reserved_keys:
            raise ReservedKeyError, 'The name "%s" is a reversed key, so please change another one' % f.__name__
        appname, path = self._get_path(f)
        if not self.rule:
            rule = '/' + '/'.join([path, f.__name__] + args)
        else:
            rule = self.rule
        rule = self._fix_url(appname, rule)
        endpoint = '.'.join([f.__module__, f.__name__])
        f.__exposed__ = True
        f.__no_rule__ = (self.parse_level == 1) or (self.parse_level == 2 and not self.rule)
        
        #add name parameter process
        if 'name' in self.kwargs:
            url_name = self.kwargs.pop('name')
            __url_names__[url_name] = endpoint
        return f, (appname, endpoint, rule, self.kwargs.copy())
    
    def __call__(self, f):
        self.parse(f)
        return f
    
def test():
    """
    >>> @expose
    ... def index():pass
    >>> print merge_rules()
    [('__main__', '__main__.index', '/__main__/index', {})]
    >>> clear_rules()
    >>> ####################################################
    >>> @expose
    ... def index(id):pass
    >>> print merge_rules()
    [('__main__', '__main__.index', '/__main__/index/<id>', {})]
    >>> clear_rules()
    >>> ####################################################
    >>> @expose()
    ... def index():pass
    >>> print merge_rules()
    [('__main__', '__main__.index', '/__main__/index', {})]
    >>> clear_rules()
    >>> ####################################################
    >>> @expose()
    ... def index(id):pass
    >>> print merge_rules()
    [('__main__', '__main__.index', '/__main__/index/<id>', {})]
    >>> clear_rules()
    >>> ####################################################
    >>> @expose('/index')
    ... def index():pass
    >>> print merge_rules()
    [('__main__', '__main__.index', '/index', {})]
    >>> clear_rules()
    >>> ####################################################
    >>> @expose(static=True)
    ... def index():pass
    >>> print merge_rules()
    [('__main__', '__main__.index', '/__main__/index', {'static': True})]
    >>> clear_rules()
    >>> ####################################################
    >>> @expose('/index')
    ... def index(id):pass
    >>> print merge_rules()
    [('__main__', '__main__.index', '/index', {})]
    >>> clear_rules()
    >>> ####################################################
    >>> @expose
    ... class A:pass
    >>> print merge_rules()
    []
    >>> clear_rules()
    >>> ####################################################
    >>> @expose
    ... class A:
    ...     def index(self):pass
    >>> print merge_rules()
    [('__main__', '__main__.A.index', '/__main__/A/index', {})]
    >>> clear_rules()
    >>> ####################################################
    >>> @expose
    ... class A:
    ...     def index(self, id):pass
    >>> print merge_rules()
    [('__main__', '__main__.A.index', '/__main__/A/index/<id>', {})]
    >>> clear_rules()
    >>> ####################################################
    >>> @expose
    ... class A:
    ...     def index(self, id):pass
    ...     @classmethod
    ...     def p(cls, id):pass
    ...     @staticmethod
    ...     def x(id):pass
    >>> print merge_rules()
    [('__main__', '__main__.A.index', '/__main__/A/index/<id>', {}), ('__main__', '__main__.A.p', '/__main__/A/p/<id>', {}), ('__main__', '__main__.A.x', '/__main__/A/x/<id>', {})]
    >>> clear_rules()
    >>> ####################################################
    >>> @expose
    ... class A:
    ...     @expose('/index')
    ...     def index(self, id):pass
    >>> print merge_rules()
    [('__main__', '__main__.A.index', '/index', {})]
    >>> clear_rules()
    >>> ####################################################
    >>> @expose('/user')
    ... class A:
    ...     @expose('/index')
    ...     def index(self, id):pass
    ...     def hello(self):pass
    >>> print merge_rules()
    [('__main__', '__main__.A.index', '/index', {}), ('__main__', '__main__.A.hello', '/user/hello', {})]
    >>> clear_rules()
    >>> ####################################################
    >>> @expose('/user')
    ... class A(object):
    ...     @expose('/index')
    ...     def index(self, id):pass
    ...     def hello(self):pass
    >>> print merge_rules()
    [('__main__', '__main__.A.index', '/index', {}), ('__main__', '__main__.A.hello', '/user/hello', {})]
    >>> clear_rules()
    >>> ####################################################
    >>> app_rules = {'__main__':'/wiki'}
    >>> set_app_rules(app_rules)
    >>> @expose('/user')
    ... class A(object):
    ...     @expose('/index')
    ...     def index(self, id):pass
    ...     def hello(self):pass
    >>> print merge_rules()
    [('__main__', '__main__.A.index', '/wiki/index', {}), ('__main__', '__main__.A.hello', '/wiki/user/hello', {})]
    >>> clear_rules()
    >>> ####################################################
    >>> set_app_rules({})
    >>> @expose
    ... class A:
    ...     @expose('/index', name='index', static=True)
    ...     def index(self, id):pass
    >>> print merge_rules()
    [('__main__', '__main__.A.index', '/index', {'static': True})]
    >>> clear_rules()
    >>> ####################################################
    >>> set_app_rules({})
    >>> @expose
    ... class A:
    ...     @expose
    ...     def index(self, id):pass
    >>> print merge_rules()
    [('__main__', '__main__.A.index', '/__main__/A/index/<id>', {})]
    >>> clear_rules()
    >>> ####################################################
    >>> set_app_rules({})
    >>> @expose
    ... class A:
    ...     @expose()
    ...     def index(self, id):pass
    >>> print merge_rules()
    [('__main__', '__main__.A.index', '/__main__/A/index/<id>', {})]
    >>> clear_rules()
    >>> ####################################################
    >>> @expose
    ... class A:
    ...     @expose(name='index', static=True)
    ...     def index(self, id):pass
    >>> print merge_rules()
    [('__main__', '__main__.A.index', '/__main__/A/index/<id>', {'static': True})]
    >>> clear_rules()
    >>> ####################################################
    >>> @expose('/')
    ... class A:
    ...     def index(self, id):pass
    >>> print merge_rules()
    [('__main__', '__main__.A.index', '/index/<id>', {})]
    >>> clear_rules()
    >>> ####################################################
    >>> def static():pass
    >>> n = expose('/static', static=True)(static)
    >>> print merge_rules()
    [('__main__', '__main__.static', '/static', {'static': True})]
    >>> clear_rules()
    >>> ####################################################
    >>> @expose
    ... class A:
    ...     @expose('/index', name='index', static=True)
    ...     def index(self, id):pass
    >>> print merge_rules()
    [('__main__', '__main__.A.index', '/index', {'static': True})]
    >>> print __url_names__
    {'index': '__main__.A.index'}
    >>> clear_rules()
    
    """
    
#if __name__ == '__main__':
#    @expose
#    class A:
#        @expose('/index')
#        def index(self, id):pass
#        
#        @classmethod
#        @expose('/hello')
#        def p(cls):
#            pass
#        
#        def x(self):
#            pass
#        
#        @staticmethod
#        def t():
#            pass
#        
#    print merge_rules()
