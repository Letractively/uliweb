####################################################################
# Author: Limodou@gmail.com
# License: BSD
####################################################################

import os, sys
import cgi
import types
from werkzeug import Request as OriginalRequest, Response as OriginalResponse
from werkzeug import ClosingIterator, Local, LocalManager, BaseResponse
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.routing import Map

import template
from storage import Storage
import dispatch
from uliweb.utils.common import (pkg, log, sort_list, import_attr, 
    myimport, wraps, norm_path, cache_get)
from uliweb.utils.pyini import Ini
import uliweb as conf
#from rules import Mapping, add_rule
import rules

try:
    set
except:
    from sets import Set as set

conf.local = local = Local()
local_manager = LocalManager([local])
conf.url_map = Map()
__app_dirs__ = {}

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

def function(fname, *args, **kwargs):
    func = conf.settings.get_var('FUNCTIONS/'+fname)
    if func:
        if args or kwargs:
            return import_attr(func)(*args, **kwargs)
        else:
            return import_attr(func)
    else:
        raise Exception, "Can't find the function [%s] in settings" % func
 
def json(data, unicode=False):
    from js import json_dumps
        
    if unicode:
        ensure_ascii = True
    else:
        ensure_ascii = False
    
    if callable(data):
        @wraps(data)
        def f(*arg, **kwargs):
            ret = data(*arg, **kwargs)
            return Response(json_dumps(ret), content_type='application/json; charset=utf-8')
        return f
    else:
        return Response(json_dumps(data), content_type='application/json; charset=utf-8')

def expose(rule=None, **kwargs):
    e = rules.Expose(rule, **kwargs)
    if e.parse_level == 1:
        return rule
    else:
        return e

def POST(rule, **kw):
    kw['methods'] = ['POST']
    return expose(rule, **kw)

def GET(rule, **kw):
    kw['methods'] = ['GET']
    return expose(rule, **kw)

def url_for(endpoint, **values):
    if callable(endpoint):
        endpoint = endpoint.__module__ + '.' + endpoint.__name__
    _external = values.pop('_external', False)
    if endpoint in rules.__url_names__:
        endpoint = rules.__url_names__[endpoint]
    return conf.local.url_adapter.build(endpoint, values, force_external=_external)

def get_app_dir(app):
    """
    Get an app's directory
    """
    path = __app_dirs__.get(app)
    if path is not None:
        return path
    else:
        p = app.split('.')
        try:
            path = pkg.resource_filename(p[0], '')
        except ImportError, e:
            log.exception(e)
            path = ''
        if len(p) > 1:
            path = os.path.join(path, *p[1:])
        
        __app_dirs__[app] = path
        return path

def get_apps(apps_dir, include_apps=None, settings_file='settings.ini'):
    include_apps = include_apps or []
    inifile = norm_path(os.path.join(apps_dir, settings_file))
    apps = []
    if not os.path.exists(apps_dir):
        return apps
    if os.path.exists(inifile):
        x = cache_get(inifile, lambda x:Ini(x), 'ini')
        if x:
            apps = x.GLOBAL.get('INSTALLED_APPS', [])
    if not apps and os.path.exists(apps_dir):
        for p in os.listdir(apps_dir):
            if os.path.isdir(os.path.join(apps_dir, p)) and p not in ['.svn', 'CVS'] and not p.startswith('.') and not p.startswith('_'):
                apps.append(p)
    
    apps.extend(include_apps)
    #process dependencies
    s = apps[:]
    visited = set()
    while s:
        p = s.pop()
        if p in visited:
            continue
        else:
            configfile = os.path.join(get_app_dir(p), 'config.ini')
            
            if os.path.exists(configfile):
                x = Ini(configfile)
                for i in x.get_var('DEFAULT/REQUIRED_APPS', []):
                    if i not in apps:
                        apps.append(i)
                    if i not in visited:
                        s.append(i)
            visited.add(p)

    return apps

class Loader(object):
    def __init__(self, tmpfilename, vars, env, dirs, notest=False):
        self.tmpfilename = tmpfilename
        self.dirs = dirs
        self.vars = vars
        self.env = env
        self.notest = notest
        
    def get_source(self, exc_type, exc_value, exc_info, tb):
        from uliweb.core.template import Template
        t = Template('', self.vars, self.env, self.dirs)
        t.set_filename(self.tmpfilename)
        use_temp_flag, filename, text = t.get_parsed_code()
        
        if exc_type is SyntaxError:
            import re
            r = re.search(r'line (\d+)', str(exc_value))
            lineno = int(r.group(1))
        else:
            lineno = tb.tb_frame.f_lineno
        return self.tmpfilename, lineno, text 
    
    def test(self, filename):
        if self.notest:
            return True
        return filename.endswith('.html')
    
class Dispatcher(object):
    installed = False
    def __init__(self, apps_dir='apps', include_apps=None, start=True, default_settings=None, settings_file='settings.ini'):
        conf.application = self
        self.debug = False
        self.include_apps = include_apps or []
        self.default_settings = default_settings or {}
        self.settings_file = settings_file
        if not Dispatcher.installed:
            self.init(apps_dir)
            dispatch.call(self, 'startup_installed')
            self.init_urls()
            
        if start:
            dispatch.call(self, 'startup')
    
    def init(self, apps_dir):
        conf.apps_dir = apps_dir
        Dispatcher.apps_dir = apps_dir
        Dispatcher.apps = get_apps(self.apps_dir, self.include_apps)
        Dispatcher.modules = self.collect_modules()
        self.install_settings(self.modules['settings'])
        Dispatcher.settings = conf.settings
        Dispatcher.env = self._prepare_env()
        Dispatcher.template_dirs = self.get_template_dirs()
        
        #begin to start apps
        self.install_apps()
        
        dispatch.call(self, 'after_init_apps')

        Dispatcher.url_map = conf.url_map
        self.install_views(self.modules['views'])
        #process dispatch hooks
        self.dispatch_hooks()
        
        self.debug = conf.settings.GLOBAL.get('DEBUG', False)
        dispatch.call(self, 'prepare_default_env', Dispatcher.env)
        Dispatcher.default_template = pkg.resource_filename('uliweb.core', 'default.html')
        
        Dispatcher.installed = True
        
    def _prepare_env(self):
        env = Storage({})
        env['url_for'] = url_for
        env['redirect'] = redirect
        env['error'] = error
        env['application'] = self
        env['settings'] = conf.settings
        env['json'] = json
        return env
    
    def get_file(self, filename, dir='static'):
        """
        get_file will search from apps directory
        """
        if os.path.exists(filename):
            return filename
        dirs = self.apps
        if dir:
            fname = os.path.join(dir, filename)
        else:
            fname = filename
        for d in reversed(dirs):
            path = pkg.resource_filename(d, fname)
            if os.path.exists(path):
                return path
        return None

    def template(self, filename, vars=None, env=None, dirs=None, default_template=None):
        vars = vars or {}
        dirs = dirs or self.template_dirs
        env = env or self.get_view_env()
        
        if self.debug:
            def _compile(code, filename, action, env, Loader=Loader):
                env['__loader__'] = Loader(filename, vars, env, dirs, notest=True)
                try:
                    return compile(code, filename, 'exec')
                except:
#                    file('out.html', 'w').write(code)
                    raise
            
            return template.template_file(filename, vars, env, dirs, default_template, compile=_compile)
        else:
            return template.template_file(filename, vars, env, dirs, default_template)
    
    def render_text(self, text, vars=None, env=None, dirs=None, default_template=None):
        vars = vars or {}
        env = env or self.get_view_env()
        dirs = dirs or self.template_dirs
        
        return template.template(text, vars, env, dirs, default_template)
    
    def render(self, templatefile, vars, env=None, dirs=None, default_template=None, content_type='text/html', status=200):
        return Response(self.template(templatefile, vars, env, dirs, default_template=default_template), status=status, content_type=content_type)
    
    def _page_not_found(self, description=None, **kwargs):
        description = 'The requested URL "{{=url}}" was not found on the server.'
        text = """<h1>Page Not Found</h1>
    <p>%s</p>
    <h3>Current URL Mapping is</h3>
    <table border="1">
    <tr><th>URL</th><th>View Functions</th></tr>
    {{for url, methods, endpoint in urls:}}
    <tr><td>{{=url}} {{=methods}}</td><td>{{=endpoint}}</td></tr>
    {{pass}}
    </table>
    """ % description
        return Response(template.template(text, kwargs), status=404, content_type='text/html')
        
    def not_found(self, e):
        if self.debug:
            urls = []
            for r in self.url_map.iter_rules():
                if r.methods:
                    methods = ' '.join(list(r.methods))
                else:
                    methods = ''
                urls.append((r.rule, methods, r.endpoint))
            urls.sort()
            return self._page_not_found(url=local.request.path, urls=urls)
        tmp_file = template.get_templatefile('404'+conf.settings.GLOBAL.TEMPLATE_SUFFIX, self.template_dirs)
        if tmp_file:
            response = self.render(tmp_file, {'url':local.request.path}, status=404)
        else:
            response = e
        return response
    
    def internal_error(self, e):
        tmp_file = template.get_templatefile('500'+conf.settings.GLOBAL.TEMPLATE_SUFFIX, self.template_dirs)
        if tmp_file:
            response = self.render(tmp_file, {'url':local.request.path}, status=500)
        else:
            response = e
        log.exception(e)
        return response
    
    def get_env(self, env=None):
        e = Storage(self.env.copy())
        if env:
            e.update(env)
        return e
    
    def prepare_request(self, request, endpoint):
        #binding some variable to request
        request.settings = conf.settings
        request.application = self
        
        #get handler
        _klass = None
        if isinstance(endpoint, (str, unicode)):
            module, func = endpoint.rsplit('.', 1)
            #if the module contains a class name, then import the class
            #it set by expose()
            if module.endswith('__class__'):
                module, cls = module.rsplit('.', 1)
                cls = cls[:-9]
            mod = __import__(module, {}, {}, [''])
            if cls:
                #create class instance
                _klass = getattr(mod, cls)()
                handler = getattr(_klass, func)
            else:
                handler = getattr(mod, func)
        elif callable(endpoint):
            handler = endpoint
            mod = sys.modules[handler.__module__]
        
        request.appname = ''
        for p in self.apps:
            t = p + '.'
            if handler.__module__.startswith(t):
                request.appname = p
                break
        request.function = handler.__name__
        return mod, _klass, handler
    
    def call_view(self, mod, cls, handler, request, response=None, **values):
        #get env
        env = self.get_view_env()
        
        #if there is __begin__ then invoke it, if __begin__ return None, it'll
        #continue running
        if hasattr(mod, '__begin__'):
            f = getattr(mod, '__begin__')
            result = self._call_function(f, request, response, env)
            if result is not None:
                return self.wrap_result(result, request, response, env)
        
        if hasattr(cls, '__begin__'):
            f = getattr(cls, '__begin__')
            result = self._call_function(f, request, response, env)
            if result is not None:
                return self.wrap_result(result, request, response, env)
        
        result = self.call_handler(handler, request, response, env, **values)

        result1 = None
        if hasattr(mod, '__end__'):
            f = getattr(mod, '__end__')
            result1, env = self._call_function(f, request, response, env)
            if result1 is not None:
                return self.wrap_result(result1, request, response, env)
        
        result1 = None
        if hasattr(cls, '__end__'):
            f = getattr(cls, '__end__')
            result1, env = self._call_function(f, request, response, env)
            if result1 is not None:
                return self.wrap_result(result1, request, response, env)

        return result
        
    def wrap_result(self, result, request, response, env):
#        #process ajax invoke, return a json response
#        if request.is_xhr and isinstance(result, dict):
#            result = Response(JSON.dumps(result), content_type='application/json')

        if isinstance(result, dict):
            result = Storage(result)
            if hasattr(response, 'template'):
                tmpfile = response.template
            else:
                tmpfile = request.function + conf.settings.GLOBAL.TEMPLATE_SUFFIX
            content_type = response.content_type
            
            #if debug mode, then display a default_template
            if self.debug:
                d = ['default.html', self.default_template]
            else:
                d = None
            response = self.render(tmpfile, result, env=env, default_template=d, content_type=content_type)
        elif isinstance(result, (str, unicode)):
            response = Response(result, content_type='text/html')
        elif isinstance(result, (Response, BaseResponse)):
            response = result
        else:
            response = Response(str(result), content_type='text/html')
        return response
    
    def get_view_env(self):
        #prepare local env
        local_env = {}
        
        #process before view call
        dispatch.call(self, 'prepare_view_env', local_env, local.request)
        
        local_env['application'] = local.application
        local_env['request'] = conf.request
        local_env['response'] = conf.response
        local_env['url_for'] = url_for
        local_env['redirect'] = redirect
        local_env['error'] = error
        local_env['settings'] = conf.settings
        local_env['json'] = json
        
        return self.get_env(local_env)
       
    def _call_function(self, handler, request, response, env, **values):
        
        for k, v in env.iteritems():
            handler.func_globals[k] = v
        
        handler.func_globals['env'] = env
        
        result = handler(**values)
        if isinstance(result, ResponseProxy):
            result = local.response
        return result
    
    def call_handler(self, handler, request, response, env, **values):
        result = self._call_function(handler, request, response, env, **values)
        return self.wrap_result(result, request, response, env)
            
    def collect_modules(self, check_view=True):
        modules = {}
        views = set()
        settings = []

        inifile = pkg.resource_filename('uliweb.core', 'default_settings.ini')
        settings.insert(0, inifile)
        
        def enum_views(views_path, appname, subfolder=None, pattern=None):
            for f in os.listdir(views_path):
                fname, ext = os.path.splitext(f)
                if os.path.isfile(os.path.join(views_path, f)) and ext in ['.py', '.pyc', '.pyo'] and fname!='__init__':
                    if pattern:
                        import fnmatch
                        if not fnmatch.fnmatch(f, pattern):
                            continue
                    if subfolder:
                        views.add('.'.join([appname, subfolder, fname]))
                    else:
                        views.add('.'.join([appname, fname]))

        for p in self.apps:
            path = get_app_dir(p)
            #deal with views
            if check_view:
                views_path = os.path.join(path, 'views')
                if os.path.exists(views_path) and os.path.isdir(views_path):
                    enum_views(views_path, p, 'views')
                else:
                    enum_views(path, p, pattern='views*')
            #deal with settings
            inifile =os.path.join(get_app_dir(p), 'settings.ini')
            
            if os.path.exists(inifile):
                settings.append(inifile)

        set_ini = os.path.join(self.apps_dir, self.settings_file)
        if os.path.exists(set_ini):
            settings.append(set_ini)
        
        modules['views'] = list(views)
        modules['settings'] = settings
        return modules
    
    def install_views(self, views):
        for v in views:
            try:
                myimport(v)
            except Exception, e:
                log.exception(e)
         
    def init_urls(self):
        #set app rules
        rules.set_app_rules(conf.settings.get('URL', {}))
        
        #initialize urls
        for v in rules.merge_rules():
            appname, endpoint, url, kw = v
            static = kw.pop('static', None)
            if static:
                conf.static_views.append(endpoint)
            rules.add_rule(conf.url_map, url, endpoint, **kw)
    
    def install_apps(self):
        for p in self.apps:
            try:
                myimport(p)
            except ImportError, e:
                pass
            except Exception, e:
                log.exception(e)
            
    def install_settings(self, s):
        env = dispatch.get(self, 'init_settings_env')
        conf.settings = Ini(env=env)
        for v in s:
            conf.settings.read(v)
        conf.settings.update(self.default_settings)
        
        #process FILESYSTEM_ENCODING
        if conf.settings.GLOBAL.FILESYSTEM_ENCODING:
            conf.settings.GLOBAL.FILESYSTEM_ENCODING = sys.getfilesystemencoding() or conf.settings.GLOBAL.DEFAULT_ENCODING
            
    def dispatch_hooks(self):
        #process DISPATCH hooks
        d = conf.settings.get('BINDS', {})
        for topic, args in d.iteritems():
            if not args:
                continue
            is_wrong = False
            if isinstance(args, (tuple, list)):
                if len(args) != 2:
                    is_wrong = True
                if not isinstance(args[1], dict):
                    is_wrong = True
                if not is_wrong:
                    dispatch.bind(topic, **args[1])(args[0])
            elif isinstance(args, (str, unicode)):
                dispatch.bind(topic)(args)
            else:
                is_wrong = True
            if is_wrong:
                log.error('BINDS definition should be "url=endpoint" or "url=endpoint, {"args":value1,...}"')
                raise Exception, 'BINDS definition [%s=%r] is not right' % (topic, args)
                
        d = conf.settings.get('EXPOSES', {})
        for url, args in d.iteritems():
            if not args:
                continue
            is_wrong = False
            if isinstance(args, (tuple, list)):
                if len(args) != 2:
                    is_wrong = True
                if not isinstance(args[1], dict):
                    is_wrong = True
                if not is_wrong:
                    expose(url, **args[1])(args[0])
            elif isinstance(args, (str, unicode)):
                expose(url)(args)
            else:
                is_wrong = True
            if is_wrong:
                log.error('EXPOSES definition should be "url=endpoint" or "url=endpoint, {"args":value1,...}"')
                raise Exception, 'EXPOSES definition [%s=%r] is not right' % (url, args)
                
    def get_template_dirs(self):
        """
        Get templates directory from apps, but in reversed order, so the same named template
        file will be overrided by latter defined app
        """
        template_dirs = [os.path.join(get_app_dir(p), 'templates') for p in reversed(self.apps)]
        return template_dirs
    
    def get_templateplugins_dirs(self):
        return [os.path.join(get_app_dir(p), 'template_plugins') for p in self.apps]
    
    def __call__(self, environ, start_response):
        local.application = self
        local.request = req = Request(environ)
        conf.request = RequestProxy()
        local.response = res = Response(content_type='text/html')
        conf.response = ResponseProxy()
        local.url_adapter = adapter = conf.url_map.bind_to_environ(environ)
        
        try:
            endpoint, values = adapter.match()
            
            mod, cls, handler = self.prepare_request(req, endpoint)
            
            #process static
            if endpoint in conf.static_views:
                response = self.call_view(mod, cls, handler, req, res, **values)
            else:
                response = None
                _clses = {}
                _inss = {}

                #middleware process request
                middlewares = conf.settings.GLOBAL.get('MIDDLEWARE_CLASSES', [])
                s = []
                for middleware in middlewares:
                    try:
                        order = None
                        if isinstance(middleware, tuple):
                            order, middleware = middleware
                        cls = import_attr(middleware)
                        if order is None:
                            order = getattr(cls, 'ORDER', 500)
                        s.append((order, middleware))
                    except ImportError, e:
                        log.exception(e)
                        error("Can't import the middleware %s" % middleware)
                    _clses[middleware] = cls
                middlewares = sort_list(s)
                
                for middleware in middlewares:
                    cls = _clses[middleware]
                    if hasattr(cls, 'process_request'):
                        ins = cls(self, conf.settings)
                        _inss[middleware] = ins
                        response = ins.process_request(req)
                        if response is not None:
                            break
                
                if response is None:
                    try:
                        response = self.call_view(mod, cls, handler, req, res, **values)
                        
                    except Exception, e:
                        for middleware in reversed(middlewares):
                            cls = _clses[middleware]
                            if hasattr(cls, 'process_exception'):
                                ins = _inss.get(middleware)
                                if not ins:
                                    ins = cls(self, conf.settings)
                                response = ins.process_exception(req, e)
                                if response:
                                    break
                        raise
                        
                else:
                    response = res
                    
                for middleware in reversed(middlewares):
                    cls = _clses[middleware]
                    if hasattr(cls, 'process_response'):
                        ins = _inss.get(middleware)
                        if not ins:
                            ins = cls(self, conf.settings)
                        response = ins.process_response(req, response)
                
            #endif
            
        except HTTPError, e:
            response = self.render(e.errorpage, Storage(e.errors))
        except NotFound, e:
            response = self.not_found(e)
        except HTTPException, e:
            response = e
        except Exception, e:
            if not self.settings.get_var('GLOBAL/DEBUG'):
                response = self.internal_error(e)
            else:
#                log.exception(e)
                raise
        return ClosingIterator(response(environ, start_response),
                               [local_manager.cleanup])
