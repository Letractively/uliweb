####################################################################
# Author: Limodou@gmail.com
# License: GPLv2
####################################################################

#defautl global settings

__all__ = ['expose', 'Dispatcher', 'url_for', 'get_app_dir', 'redirect']

import os, cgi
from webob import Request, Response
#from werkzeug import Request, Response
from werkzeug import ClosingIterator, Local, LocalManager, BaseResponse
from werkzeug.exceptions import HTTPException, NotFound, InternalServerError

from uliweb.core.rules import Mapping, add_rule
from uliweb.core import template
from uliweb.core.storage import Storage
from uliweb.core.plugin import *

APPS_DIR = 'apps'

local = Local()
local_manager = LocalManager([local])

url_map = Mapping()
_urls = []
_static_views = []
__use_urls = False
__app_dirs = {}
settings = None

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
        if __use_urls:
            return rule
        f = rule
        import inspect
        args = inspect.getargspec(f)[0]
        if args :
            args = ['<%s>' % x for x in args]
        appname = f.__module__.split('.')[1]
        rule = '/' + '/'.join([appname, f.__name__] + args)
        kw['endpoint'] = f.__module__ + '.' + f.__name__
        _urls.append((rule, kw))
        if static:
            _static_views.append(kw['endpoint'])
        if 'static' in kw:
            kw.pop('static')
        add_rule(url_map, rule, **kw)
        return f
        
    def decorate(f, rule=rule):
        if __use_urls:
            return f
        kw['endpoint'] = f.__module__ + '.' + f.__name__
        if callable(rule):
            import inspect
            args = inspect.getargspec(f)[0]
            if args :
                args = ['<%s>' % x for x in args]
            appname = f.__module__.split('.')[1]
            rule = '/' + '/'.join([appname, f.__name__] + args)
        _urls.append((rule, kw))
        if static:
            _static_views.append(kw['endpoint'])
        if 'static' in kw:
            kw.pop('static')
        add_rule(url_map, rule, **kw)
        return f
    return decorate

def url_for(endpoint, _external=False, **values):
    return local.url_adapter.build(endpoint, values, force_external=_external)

def import_func(path):
    module, func = path.rsplit('.', 1)
    mod = __import__(module, {}, {}, [''])
    return getattr(mod, func)

class HTTPError(Exception):
    def __init__(self, errorpage=None, **kwargs):
        self.errorpage = errorpage or settings.ERROR_PAGE
        self.errors = kwargs

    def __str__(self):
        return self.e
   
def redirect(location, code=302):
    response = Response(
        '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">\n'
        '<title>Redirecting...</title>\n'
        '<h1>Redirecting...</h1>\n'
        '<p>You should be redirected automatically to target URL: '
        '<a href="%s">%s</a>.  If not click the link.' %
        (cgi.escape(location), cgi.escape(location)), status=str(code), content_type='text/html')
    response.headers['Location'] = location
    return response

def errorpage(message='', errorpage=None, request=None, appname=None, **kwargs):
    kwargs.setdefault('message', message)
    if request:
        kwargs.setdefault('link', request.url)
    raise HTTPError(errorpage, **kwargs)

def static_serve(request, filename, check=True, dir=None):
    for p in request.application.apps:
        if not dir:
            path = os.path.normpath(os.path.join(get_app_dir(p), 'static')).replace('\\', '/')
        else:
            path = dir
        f = os.path.normpath(os.path.join(path, filename)).replace('\\', '/')
        if check and not f.startswith(path):
            errorpage("You can only visit the files under static directory.")
        if os.path.exists(f):
            from uliweb.core.FileApp import return_file
            return return_file(f)
    raise NotFound("Can't found the file %s" % filename)


def get_app_dir(app):
    """
    Get an app's directory
    """
    path = __app_dirs.get(app)
    if path:
        return path
    else:
        try:
            m = __import__(app, {}, {}, [''])
            path = os.path.dirname(m.__file__)
        except ImportError:
            path = ''
        __app_dirs[app] = path
        return path
        
class Loader(object):
    def __init__(self, tmpfilename, vars, env, dirs, notest=False):
        self.tmpfilename = tmpfilename
        self.dirs = dirs
        self.vars = vars
        self.env = env
        self.notest = notest
        
    def get_source(self, exc_type, exc_value, exc_info, tb):
        f, t = template.render_file(self.tmpfilename, self.vars, self.env, self.dirs)
        if exc_type is SyntaxError:
            import re
            r = re.search(r'line (\d+)', str(exc_value))
            lineno = int(r.group(1))
        else:
            lineno = tb.tb_frame.f_lineno
        return self.tmpfilename, lineno, t 
    
    def test(self, filename):
        if self.notest:
            return True
        return filename.endswith('.html')

import time        
class Dispatcher(object):
    installed = False
    def __init__(self, apps_dir=APPS_DIR, use_urls=None):
        global __use_urls
        self.debug = False
        self.use_urls = __use_urls = use_urls
        if not Dispatcher.installed:
            self.init(apps_dir)
            callplugin(self, 'startup_installed')
            
        callplugin(self, 'startup')
        
    def init(self, apps_dir):
        global APPS_DIR, url_map, _static_urls
        import __builtin__
        setattr(__builtin__, 'expose', expose)
        setattr(__builtin__, 'plugin', plugin)
        setattr(__builtin__, 'application', self)
        
        APPS_DIR = apps_dir
        Dispatcher.apps_dir = apps_dir
        Dispatcher.apps = self.get_apps()
        #add urls.py judgement
        flag = True
        if self.use_urls is None or self.use_urls is True:
            try:
                import urls
                from uliweb.core import rules
                url_map = urls.url_map
                _static_views = rules._static_views
                flag = False
            except ImportError:
                pass
        Dispatcher.modules = self.collect_modules(flag)
        Dispatcher.url_map = url_map
        if flag:
            self.install_views(self.modules['views'])
            Dispatcher.url_infos = _urls
        else:
            Dispatcher.url_infos = []
        self.install_settings(self.modules['settings'])
        Dispatcher.template_dirs = self.get_template_dirs()
        Dispatcher.env = self._prepare_env()
        Dispatcher.settings = settings
        self.debug = settings.get('DEBUG', False)
        Dispatcher.template_env = Storage(Dispatcher.env.copy())
        callplugin(self, 'prepare_default_env', Dispatcher.env)
        callplugin(self, 'prepare_template_env', Dispatcher.template_env)
        Dispatcher.installed = True
        
    def _prepare_env(self):
        env = Storage({})
        env['url_for'] = url_for
        env['redirect'] = redirect
        env['error'] = errorpage
        env['url_map'] = url_map
        env['render'] = self.render
        env['template'] = self.template
        env['settings'] = settings
        from werkzeug import html, xhtml
        env['html'] = html
        env['xhtml'] = xhtml
        from uliweb.core import Form
        env['Form'] = Form
        env['get_file'] = self.get_file
        return env
    
    def get_apps(self):
        try:
            import settings
            if hasattr(settings, 'INSTALLED_APPS'):
                return getattr(settings, 'INSTALLED_APPS')
        except ImportError:
            pass
        
        s = []
        for p in os.listdir(self.apps_dir):
            if os.path.isdir(os.path.join(self.apps_dir, p)) and p not in ['.svn', 'CVS'] and not p.startswith('.') and not p.startswith('_'):
                s.append(p)
        return s
        
    def get_file(self, filename, request=None, dirname='files'):
        """
        get_file will search from apps directory
        """
        if os.path.exists(filename):
            return filename
        if request:
            dirs = [os.path.join(get_app_dir(x), dirname) for x in [request.appname] + self.apps]
        else:
            dirs = [os.path.join(get_app_dir(x), dirname) for x in self.apps]
        for d in dirs:
            path = os.path.join(d, filename)
            if os.path.exists(path):
                return path
        return None
#        errorpage("Can't find the file %s" % filename)

    def template(self, templatefile, vars, env=None, dirs=None, request=None):
        dirs = dirs or self.template_dirs
        env = self.get_template_env(env)
        if request:
            dirs = [os.path.join(get_app_dir(request.appname), 'templates')] + dirs
        if self.debug:
            def debug_template(filename, vars, env, dirs):
                def _compile(code, filename, action):
                    __loader__ = Loader(filename, vars, env, dirs, notest=True)
                    return compile(code, filename, 'exec')
                vars = vars or {}
                env = env or {}
                fname, code = template.render_file(filename, vars, env, dirs)
                out = template.Out()
                template._prepare_run(vars, env, out)
                
                if isinstance(code, (str, unicode)):
                    code = _compile(code, fname, 'exec')
                __loader__ = Loader(fname, vars, env, dirs)
                exec code in env, vars
                return out.getvalue()
            
            return debug_template(templatefile, vars, env, dirs)
        else:
            return template.template_file(templatefile, vars, env, dirs)
    
    def render(self, templatefile, vars, env=None, dirs=None, request=None):
        return Response(self.template(templatefile, vars, env, dirs, request), content_type='text/html')
    
    def _page_not_found(self, description=None, **kwargs):
        if not description:
            description = "Can't visit the URL \"{{=url}}\""
        text = """<h1>Page Not Found</h1>
    <p>%s</p>
    <h3>Current URL Mapping is</h3>
    <table border="1">
    <tr><th>URL</th><th>View Functions</th></tr>
    {{for url, endpoint in urls:}}
    <tr><td>{{=url}}</td><td>{{=endpoint}}</td></tr>
    {{pass}}
    </table>
    """ % description
        return Response(template.template(text, kwargs), status='404', content_type='text/html')
        
    def not_found(self, request, e):
        if self.debug:
            urls = []
            for r in self.url_map.iter_rules():
                urls.append((r.rule, r.endpoint))
            urls.sort()
            return self._page_not_found(description=e.description, url=request.path, urls=urls)
        tmp_file = template.get_templatefile('404'+settings.TEMPLATE_SUFFIX, self.template_dirs)
        if tmp_file:
            response = self.render(tmp_file, {'url':request.path})
            response.status = '404'
        else:
            response = e
        return response
    
    def internal_error(self, request, e):
        tmp_file = template.get_templatefile('500'+settings.TEMPLATE_SUFFIX, self.template_dirs)
        if tmp_file:
            response = self.render(tmp_file, {'url':request.path})
            response.status = '500'
        else:
            response = e
        return response
    
    def get_template_env(self, env=None):
        e = self.template_env
        if env:
            e.update(env)
        return e
    
    def call_endpoint(self, mod, handler, request, response=None, **values):
        #if there is __begin__ then invoke it, if __begin__ return None, it'll
        #continue running
        if hasattr(mod, '__begin__'):
            f = getattr(mod, '__begin__')
            result, env = self._call_function(f, request, response)
            if result:
                return self.wrap_result(result, request, response, env)
        
        result = self.call_handler(handler, request, response, **values)
        return result
        
    def wrap_result(self, result, request, response, env=None):
        env = env or self.env
        if isinstance(result, dict):
            result = Storage(result)
            if hasattr(response, 'template') and response.template:
                tmpfile = response.template
            else:
                tmpfile = request.function + settings.TEMPLATE_SUFFIX
            response = self.render(tmpfile, result, env=env, request=request)
        elif isinstance(result, (str, unicode)):
            response = Response(result, content_type='text/html')
        elif isinstance(result, (Response, BaseResponse)):
            response = result
        else:
            response = Response(str(result), content_type='text/html')
        return response
    
    def _call_function(self, handler, request, response=None, **values):
        response = response or Response(content_type='text/html')
        
        #prepare local env
        local_env = {}
        local_env['application'] = self
        local_env['request'] = request
        local_env['response'] = response
        local_env['url_for'] = url_for
        local_env['redirect'] = redirect
        local_env['error'] = errorpage
        local_env['settings'] = settings
        
        for k, v in local_env.iteritems():
            handler.func_globals[k] = v
        
        env = self.get_template_env(local_env)
        handler.func_globals['env'] = env
        
        result = handler(**values)
        return result, env
    
    def call_handler(self, handler, request, response=None, **values):
        result, env = self._call_function(handler, request, response, **values)
        return self.wrap_result(result, request, response, env)
            
    def collect_modules(self, check_view=True):
        modules = {}
        views = set()
        settings = []
        settings_files = ['.'.join([os.path.basename(self.apps_dir), 'settings']) for x in ['.py', '.pyc', '.pyo']
            if os.path.exists(os.path.join(self.apps_dir, 'settings%s' % x))]
        if settings_files:
            settings.append(settings_files[0])
        
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
            if p.startswith('.') or p.startswith('_') or p.startswith('CVS'):
                continue
            if os.path.isdir(path):
                #deal with views
                if check_view:
                    views_path = os.path.join(p, 'views')
                    if os.path.exists(views_path) and os.path.isdir(views_path):
                        enum_views(views_path, p, 'views')
                    else:
                        enum_views(path, p, pattern='views*')
                #deal with settings
                if p in self.apps:
                    settings_files = ['.'.join([p, 'settings']) for x in ['.py', '.pyc', '.pyo']
                        if os.path.exists(os.path.join(get_app_dir(p), 'settings%s' % x))]
                    if settings_files:
                        settings.insert(0, settings_files[0])
           
        modules['views'] = list(views)
        modules['settings'] = settings
        return modules
    
    def install_views(self, views):
        for v in views:
            __import__(v, {}, {}, [''])
            
    def install_settings(self, s):
        global settings
        s.insert(0, 'uliweb.core.default_config')
        settings = Storage({})
        for v in s:
            mod = __import__(v, {}, {}, [''])
            for k in dir(mod):
                #if k is already exists in settings, then skip it
                if k.startswith('_') or not k.isupper() or k in settings:
                    pass
                else:
                    settings[k] = getattr(mod, k)
            
    def get_template_dirs(self):
        template_dirs = [os.path.join(get_app_dir(p), 'templates') for p in self.apps]
        return template_dirs
    
    def __call__(self, environ, start_response):
        local.application = self
        req = Request(environ)
        
        local.url_adapter = adapter = url_map.bind_to_environ(environ)
        try:
            endpoint, values = adapter.match()
            
            #binding some variable to request
            req.settings = settings
            req.application = self
            
            #get handler
            module, func = endpoint.rsplit('.', 1)
            mod = __import__(module, {}, {}, [''])
            handler = getattr(mod, func)
            
            for p in self.apps:
                t = p + '.'
                if handler.__module__.startswith(t):
                    req.appname = p
                    break
            req.function = handler.__name__
            
            #process static
            if endpoint in _static_views:
                res = Response(content_type='text/html')
                response = self.call_endpoint(mod, handler, req, res, **values)
            else:
                #middleware process request
                middlewares = settings.get('MIDDLEWARE_CLASSES', [])
                response = None
                _clses = {}
                _inss = {}
                for middleware in middlewares:
                    try:
                        cls = import_func(middleware)
                    except ImportError:
                        errorpage("Can't import the middleware %s" % middleware)
                    _clses[middleware] = cls
                    if hasattr(cls, 'process_request'):
                        ins = cls(self, settings)
                        _inss[middleware] = ins
                        response = ins.process_request(req)
                        if response is not None:
                            break
                
                res = Response(content_type='text/html')
                if response is None:
                    try:
                        response = self.call_endpoint(mod, handler, req, res, **values)
                        
                    except Exception, e:
                        for middleware in reversed(middlewares):
                            cls = _clses[middleware]
                            if hasattr(cls, 'process_exception'):
                                ins = _inss.get(middleware)
                                if not ins:
                                    ins = cls(self, settings)
                                response = ins.process_exception(req, e)
                                if response:
                                    break
                        else:
                            raise
                        
                else:
                    response = res
                    
                for middleware in reversed(middlewares):
                    cls = _clses[middleware]
                    if hasattr(cls, 'process_response'):
                        ins = _inss.get(middleware)
                        if not ins:
                            ins = cls(self, settings)
                        response = ins.process_response(req, response)

            #endif
            
        except HTTPError, e:
            response = self.render(e.errorpage, Storage(e.errors), request=req)
        except NotFound, e:
            response = self.not_found(req, e)
        except InternalServerError, e:
            response = self.internal_error(req, e)
        except HTTPException, e:
            response = e
        return ClosingIterator(response(environ, start_response),
                               [local_manager.cleanup])
