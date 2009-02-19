import logging
import inspect

__all__ = ['HIGH', 'MIDDLE', 'LOW', 'bind', 'call', 'get', 'unbind', 'call_once', 'get_once']

HIGH = 1    #plugin high
MIDDLE = 2
LOW = 3

_receivers = {}
_called = {}

def bind(topic, signal=None, kind=MIDDLE, nice=-1):
    """
    This is a decorator function, so you should use it as:
        
        @bind('init')
        def process_init(a, b):
            ...
    """
    def f(func):
        if not topic in _receivers:
            receivers = _receivers[topic] = []
        else:
            receivers = _receivers[topic]
        
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
        receivers.append(_f)
        return func
    return f

def unbind(topic, func):
    """
    Remove receiver function
    """
    if topic in _receivers:
        receivers = _receivers[topic]
        for i, v in enumerate(receivers):
            nice, f = v
            if f['func'] is func:
                del receivers[i]
                return

def _test(kwargs, receiver):
    signal = kwargs.get('signal', None)
    f = receiver['func']
    args = inspect.getargspec(f)[0]
    if 'signal' not in args:
        kwargs.pop('signal', None)
    _signal = receiver.get('signal')
    flag = True
    if _signal:
        if isinstance(_signal, (tuple, list)):
            if signal not in _signal:
                flag = False
        elif _signal!=signal:
            flag = False
    return flag
        
def call(sender, topic, *args, **kwargs):
    """
    Invoke receiver functions according topic, it'll invoke receiver functions one by one,
    and it'll not return anything, so if you want to return a value, you should
    use get function.
    """
    if not topic in _receivers:
        return
    items = _receivers[topic]
    items.sort()
    for i in range(len(items)):
        nice, f = items[i]
        _f = f['func']
        if callable(_f):
            if not _test(kwargs, f):
                continue
            try:
                _f(sender, *args, **kwargs)
            except:
                logging.exception('Calling dispatch point [%s] error!' % topic)
                raise
        else:
            raise Exception, "Dispatch point [%s] can't been invoked" % topic
        
def call_once(sender, topic, *args, **kwargs):
    signal = kwargs.get('signal')
    if (topic, signal) in _called:
        return
    else:
        call(sender, topic, *args, **kwargs)
        _called[(topic, signal)] = True
        
def get(sender, topic, *args, **kwargs):
    """
    Invoke receiver functions according topic, it'll invoke receiver functions one by one,
    and if one receiver function return non-None value, it'll return it and break
    the loop.
    """
    if not topic in _receivers:
        return
    items = _receivers[topic]
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
                logging.exception('Calling dispatch point [%s] error!' % topic)
                raise
            if v is not None:
                return v
        else:
            raise "Dispatch point [%s] can't been invoked" % topic

def get_once(sender, topic, *args, **kwargs):
    signal = kwargs.get('signal')
    if (topic, signal) in _called:
        return _called[(topic, signal)]
    else:
        r = get(sender, topic, *args, **kwargs)
        _called[(topic, signal)] = r
        return r
