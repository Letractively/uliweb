import logging

__all__ = ['HIGH', 'MIDDLE', 'LOW', 'plugin', 'callplugin', 'execplugin']

HIGH = 1    #plugin high
MIDDLE = 2
LOW = 3

_plugins = {}

def plugin(plugin_name, kind=MIDDLE, nice=-1):
    def f(func):
        if not plugin_name in _plugins:
            plugins = _plugins[plugin_name] = []
        else:
            plugins = _plugins[plugin_name]
        
        if nice == -1:
            if kind == MIDDLE:
                n = 500
            elif kind == HIGH:
                n = 100
            else:
                n = 900
        else:
            n = nice
        plugins.append((n, func))
        return func
    return f

def callplugin(name, *args, **kwargs):
    if not name in _plugins:
        return
    items = _plugins[name]
    items.sort()
    for i in range(len(items)):
        nice, f = items[i]
        if callable(f):
            try:
                f(*args, **kwargs)
            except:
                logging.exception('Calling plugin [%s] error!' % name)
                raise
        else:
            raise Exception, "Plugin [%s] can't been invoked" % name
        
def execplugin(name, *args, **kwargs):
    if not name in _plugins:
        return
    items = _plugins[name]
    items.sort()
    for i in range(len(items)):
        nice, f = items[i]
        if callable(f):
            try:
                v = f(*args, **kwargs)
            except:
                logging.exception('Calling plugin [%s] error!' % name)
                raise
            if v is not None:
                return v
        else:
            raise "Plugin [%s] can't been invoked" % name

