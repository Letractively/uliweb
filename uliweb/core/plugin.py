import logging

__all__ = ['HIGH', 'MIDDLE', 'LOW', 'plugin', 'callplugin', 'execplugin', 'remove_plugin']

HIGH = 1    #plugin high
MIDDLE = 2
LOW = 3

_plugins = {}

def plugin(plugin_name, signal=None, kind=MIDDLE, nice=-1):
    """
    This is a decorator function, so you should use it as:
        
        @plugin('init')
        def process_init(a, b):
            ...
    """
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
        _f = (n, {'func':func, 'signal':signal})
        plugins.append(_f)
        return func
    return f

def remove_plugin(plugin_name, func):
    """
    Remove plugin function from plugins
    """
    if plugin_name in _plugins:
        plugins = _plugins[plugin_name]
        for i, v in enumerate(plugins):
            nice, f = v
            if f['func'] is func:
                del plugins[i]
                return

def _test(kwargs, plugin):
    signal = kwargs.get('signal')
    _signal = plugin.get('signal')
    flag = True
    if _signal and _signal != signal:
        flag = False
    return flag
        
def callplugin(sender, name, *args, **kwargs):
    """
    Invoke plugin according plugin-name, it'll invoke plugin function one by one,
    and it'll not return anything, so if you want to return a value, you should
    use execplugin function.
    """
    if not name in _plugins:
        return
    items = _plugins[name]
    items.sort()
    for i in range(len(items)):
        nice, f = items[i]
        print 'xxxx', f
        _f = f['func']
        if callable(_f):
            if not _test(kwargs, f):
                continue
            try:
                _f(sender, *args, **kwargs)
            except:
                logging.exception('Calling plugin [%s] error!' % name)
                raise
        else:
            raise Exception, "Plugin [%s] can't been invoked" % name
        
def execplugin(sender, name, *args, **kwargs):
    """
    Invoke plugin according plugin-name, it'll invoke plugin function one by one,
    and if one plugin function return non-None value, it'll return it and break
    the loop.
    """
    if not name in _plugins:
        return
    items = _plugins[name]
    items.sort()
    for i in range(len(items)):
        nice, f = items[i]
        _f = f['func']
        if callable(_f):
            if not _test(kwargs, f):
                continue
            try:
                v = _f(sender, *args, **kwargs)
            except:
                logging.exception('Calling plugin [%s] error!' % name)
                raise
            if v is not None:
                return v
        else:
            raise "Plugin [%s] can't been invoked" % name

