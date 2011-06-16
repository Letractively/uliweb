import inspect
from functools import partial

__xmlrpc_functions__ = {}

def xmlrpc(func, name=None):
    global __xmlrpc_functions__
    
    if isinstance(func, str):
        return partial(xmlrpc, name=func)
            
    if inspect.isfunction(func):
        f_name = func.__name__
        if name:
            f_name = name
        __xmlrpc_functions__[f_name] = endpoint = '.'.join([func.__module__, func.__name__])
        func.xmlrpc_endpoint = (f_name, endpoint)
    elif inspect.isclass(func):
        for _name in dir(func):
            f = getattr(func, _name)
            if (inspect.ismethod(f) or inspect.isfunction(f)) and not _name.startswith('_'):
                f_name = func.__name__ + '.' + f.__name__
                endpoint = '.'.join([func.__module__, func.__name__, _name])
                if hasattr(f, 'xmlrpc_endpoint'):
                    #the method has already been decorate by xmlrpc 
                    _n, _e = f.xmlrpc_endpoint
                    __xmlrpc_functions__[_n] = endpoint
                else:
                    __xmlrpc_functions__[f_name] = endpoint
    else:
        raise Exception, "Can't support this type [%r]" % func
    return func
    
if __name__ == '__main__':
    @xmlrpc
    def f(name):
        print name
        
    print __xmlrpc_functions__
    
    @xmlrpc
    class A(object):
        def p(self):
            print 'ppp'
            
        @xmlrpc('test')
        def t(self):
            print 'ttt'
            
    print __xmlrpc_functions__
    