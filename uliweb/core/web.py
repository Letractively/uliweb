__all__ = ['Request', 'HTTPError', 'redirect', 'error', 'json',
    'POST', 'GET', 'post_view', 'pre_view', 'url_for', 'expose']

import cgi

try:
    import json as JSON
except:
    import simplejson as JSON

from werkzeug import Request as OriginalRequest, Response as OriginalResponse
import uliweb as conf
import dispatch
from uliweb.utils.common import wrap_func
from rules import add_rule

class Request(OriginalRequest):
    GET = OriginalRequest.args
    POST = OriginalRequest.form
    params = OriginalRequest.values
    FILES = OriginalRequest.files
    
class Response(OriginalResponse):
    def write(self, value):
        self.stream.write(value)
    
class RequestProxy(object):
    def instance(self):
        return conf.local.request
        
    def __getattr__(self, name):
        return getattr(conf.local.request, name)
    
    def __setattr__(self, name, value):
        setattr(conf.local.request, name, value)
        
    def __str__(self):
        return str(conf.local.request)
    
    def __repr__(self):
        return repr(conf.local.request)
            
class ResponseProxy(object):
    def instance(self):
        return conf.local.response
        
    def __getattr__(self, name):
        return getattr(conf.local.response, name)
    
    def __setattr__(self, name, value):
        setattr(conf.local.response, name, value)

    def __str__(self):
        return str(conf.local.response)
    
    def __repr__(self):
        return repr(conf.local.response)
    
class HTTPError(Exception):
    def __init__(self, errorpage=None, **kwargs):
        self.errorpage = errorpage or conf.settings.GLOBAL.ERROR_PAGE
        self.errors = kwargs

    def __str__(self):
        return repr(self.errors)
   
def redirect(location, code=302):
    response = Response(
        '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">\n'
        '<title>Redirecting...</title>\n'
        '<h1>Redirecting...</h1>\n'
        '<p>You should be redirected automatically to target URL: '
        '<a href="%s">%s</a>.  If not click the link.' %
        (cgi.escape(location), cgi.escape(location)), status=code, content_type='text/html')
    response.headers['Location'] = location
    return response

def error(message='', errorpage=None, request=None, appname=None, **kwargs):
    kwargs.setdefault('message', message)
    if request:
        kwargs.setdefault('link', request.url)
    raise HTTPError(errorpage, **kwargs)

def json(data):
    return Response(JSON.dumps(data), content_type='application/json; charset=utf-8')

class ReservedKeyError(Exception):pass

reserved_keys = ['settings', 'redirect', 'application', 'request', 'response', 'error']

def _get_rule(f):
    import inspect
    args = inspect.getargspec(f)[0]
    if args :
        args = ['<%s>' % x for x in args]
    if f.__name__ in reserved_keys:
        raise ReservedKeyError, 'The name "%s" is a reversed key, so please change another one' % f.__name__
    m = f.__module__.split('.')
    s = []
    for i in m:
        if not i.startswith('views'):
            s.append(i)
    appname = '/'.join(s)
    rule = '/' + '/'.join([appname, f.__name__] + args)
    return appname, rule
    
def expose(rule=None, **kw):
    """
    add a url assigned to the function to url_map, if rule is None, then
    the url will be function name, for example:
        
        @expose
        def index(req):
            
        will be url_map.add('index', index)
    """
    static = kw.get('static', None)
    if callable(rule):
        if conf.use_urls:
            return rule
        f = rule
        appname, rule = _get_rule(f)
        kw['endpoint'] = f.__module__ + '.' + f.__name__
        conf.urls.append((rule, kw))
        if static:
            conf.static_views.append(kw['endpoint'])
        if 'static' in kw:
            kw.pop('static')
        add_rule(conf.url_map, rule, **kw)
        return f
        
    def decorate(f, rule=rule):
        if conf.use_urls:
            return f
        if not rule:
            appname, rule = _get_rule(f)
        if callable(f):
            f_name = f.__name__
            endpoint = f.__module__ + '.' + f.__name__
        else:
            f_name = f.split('.')[-1]
            endpoint = f
            
        if f_name in reserved_keys:
            raise ReservedKeyError, 'The name "%s" is a reversed key, so please change another one' % f_name
        kw['endpoint'] = endpoint
#        if callable(rule):
#            import inspect
#            args = inspect.getargspec(f)[0]
#            if args :
#                args = ['<%s>' % x for x in args]
#            appname = f.__module__.split('.')[1]
#            rule = '/' + '/'.join([appname, f.__name__] + args)
        conf.urls.append((rule, kw))
        if static:
            conf.static_views.append(kw['endpoint'])
        if 'static' in kw:
            kw.pop('static')
        add_rule(conf.url_map, rule, **kw)
        return f
    return decorate

def pre_view(topic, *args1, **kwargs1):
    methods = kwargs1.pop('methods', None)
    signal = kwargs1.pop('signal', None)
    def _f(f):
        def _f2(*args, **kwargs):
            m = methods or []
            m = [x.upper() for x in m]
            if not m or (m and conf.local.request.method in m):
                ret = dispatch.get(conf.local.application, topic, signal=signal, *args1, **kwargs1)
                if ret:
                    return ret
            return f(*args, **kwargs)
        return wrap_func(_f2, f)
    return _f

def post_view(topic, *args1, **kwargs1):
    methods = kwargs1.pop('methods', None)
    signal = kwargs1.pop('signal', None)
    def _f(f):
        def _f2(*args, **kwargs):
            m = methods or []
            m = [x.upper() for x in m]
            ret = f(*args, **kwargs)
            ret1 = None
            if not m or (m and conf.local.request.method in m):
                ret1 = dispatch.get(conf.local.application, topic, signal=signal, *args1, **kwargs1)
            return ret or ret1
        return wrap_func(_f2, f)
    return _f
    
def POST(rule, **kw):
    kw['methods'] = ['POST']
    return expose(rule, **kw)

def GET(rule, **kw):
    kw['methods'] = ['GET']
    return expose(rule, **kw)

def url_for(endpoint, _external=False, **values):
    if callable(endpoint):
        endpoint = endpoint.__module__ + '.' + endpoint.__name__
    return conf.local.url_adapter.build(endpoint, values, force_external=_external)

