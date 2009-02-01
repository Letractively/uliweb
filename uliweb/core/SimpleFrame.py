####################################################################
# Author: Limodou@gmail.com
# License: GPLv2
####################################################################

#defautl global settings

__all__ = ['expose', 'Dispatcher', 'url_for', 'get_app_dir', 'redirect', 'static_serve']

import os, cgi
from webob import Request, Response
#from werkzeug import Request, Response
from werkzeug import ClosingIterator, Local, LocalManager, BaseResponse
from werkzeug.exceptions import HTTPException, NotFound, InternalServerError

from rules import Mapping, add_rule
import template
from storage import Storage
from plugin import *
from uliweb.utils.common import pkg, log
from uliweb.utils.pyini import Ini
try:
    set
except:
    from sets import Set as set

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
        self.errorpage = errorpage or settings.GLOBAL.ERROR_PAGE
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
    f = None
    if dir:
        fname = os.path.normpath(os.path.join(dir, filename)).replace('\\', '/')
        if check and not fname.startswith(dir):
            errorpage("You can only visit the files under static directory.")
        if os.path.exists(fname):
            f = fname
    else:
        for p in request.application.apps:
            fname = os.path.normpath(os.path.join('static', filename)).replace('\\', '/')
            if check and not fname.startswith('static/'):
                errorpage("You can only visit the files under static directory.")
            
            ff = pkg.resource_filename(p, fname)
            if os.path.exists(ff):
                f = ff
                break
    if f:
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
            path = pkg.resource_filename(app, '')
        except ImportError, e:
            log.exception(e)
            path = ''
        __app_dirs[app] = path
        return path

def get_apps(apps_dir, include_apps=None):
    include_apps = include_apps or []
    inifile = os.path.join(apps_dir, 'settings.ini')
    apps = []
    if os.path.exists(inifile):
        x = Ini(inifile)
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
                for i in x.DEFAULT.get('REQUIRED_APPS', []):
                    if i not in apps:
                        apps.append(i)
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

class Dispatcher(object):
    installed = False
    def __init__(self, apps_dir=APPS_DIR, use_urls=None, include_apps=None):
        global __use_urls
        self.debug = False
        self.use_urls = __use_urls = use_urls
        self.include_apps = include_apps or []
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
        Dispatcher.apps = get_apps(self.apps_dir, self.include_apps)
        self.install_apps()
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
        self.debug = settings.GLOBAL.get('DEBUG', False)
        Dispatcher.template_env = Storage(Dispatcher.env.copy())
        callplugin(self, 'prepare_default_env', Dispatcher.env)
        callplugin(self, 'prepare_template_env', Dispatcher.template_env)
        Dispatcher.installed = True
        self.default_template = pkg.resource_filename('uliweb.core', 'default.html')
        
    def _prepare_env(self):
        env = Storage({})
        env['url_for'] = url_for
        env['redirect'] = redirect
        env['error'] = errorpage
        env['url_map'] = url_map
#        env['render'] = self.render
#        env['template'] = self.template
        env['settings'] = settings
#        from werkzeug import html, xhtml
#        env['html'] = html
#        env['xhtml'] = xhtml
#        from uliweb.core import Form
#        env['Form'] = Form
        env['get_file'] = self.get_file
        return env
    
    def get_file(self, filename, request=None, dirname='files'):
        """
        get_file will search from apps directory
        """
        if os.path.exists(filename):
            return filename
        if request:
            dirs = [request.appname] + self.apps
        else:
            dirs = self.apps
        fname = os.path.join(dirname, filename)
        for d in dirs:
            path = pkg.resource_filename(d, fname)
            if os.path.exists(path):
                return path
        return None
#        errorpage("Can't find the file %s" % filename)

    def template(self, filename, vars, env=None, dirs=None, request=None, default_template=None):
        vars = vars or {}
        dirs = dirs or self.template_dirs
        env = self.get_template_env(env)
        if request:
            dirs = [os.path.join(get_app_dir(request.appname), 'templates')] + dirs
        if self.debug:
            def _compile(code, filename, action):
                __loader__ = Loader(filename, vars, env, dirs, notest=True)
                return compile(code, filename, 'exec')
            fname, code = template.render_file(filename, vars, env, dirs, default_template=default_template)
            out = template.Out()
            e = template._prepare_run(vars, env, out)
            #user can insert new local environment variables to env variable
            callplugin(self, 'before_render_template', e, out)
            if isinstance(code, (str, unicode)):
                code = _compile(code, fname, 'exec')
            __loader__ = Loader(fname, vars, env, dirs)
            exec code in e
            text = out.getvalue()
            output = execplugin(self, 'after_render_template', text, vars, e)
            return output or text
        else:
            fname, code = template.render_file(filename, vars, env, dirs, default_template=default_template)
            out = template.Out()
            e = template._prepare_run(vars, env, out)
            callplugin(self, 'before_render_template', e, out)
            
            if isinstance(code, (str, unicode)):
                code = compile(code, fname, 'exec')
            exec code in e
            text = out.getvalue()
            output = execplugin(self, 'after_render_template', text, vars, e)
            return output or text
    
    def render(self, templatefile, vars, env=None, dirs=None, request=None, default_template=None):
        return Response(self.template(templatefile, vars, env, dirs, request, default_template=default_template), content_type='text/html')
    
    def _page_not_found(self, description=None, **kwargs):
        description = 'The requested URL "{{=url}}" was not found on the server.'
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
            return self._page_not_found(url=request.path, urls=urls)
        tmp_file = template.get_templatefile('404'+settings.GLOBAL.TEMPLATE_SUFFIX, self.template_dirs)
        if tmp_file:
            response = self.render(tmp_file, {'url':request.path})
            response.status = '404'
        else:
            response = e
        return response
    
    def internal_error(self, request, e):
        tmp_file = template.get_templatefile('500'+settings.GLOBAL.TEMPLATE_SUFFIX, self.template_dirs)
        if tmp_file:
            response = self.render(tmp_file, {'url':request.path})
            response.status = '500'
        else:
            response = e
        return response
    
    def get_template_env(self, env=None):
        e = Storage(self.template_env.copy())
        if env:
            e.update(env)
        return e
    
    def get_execute_env(self, env=None):
        e = Storage(self.env.copy())
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
                tmpfile = request.function + settings.GLOBAL.TEMPLATE_SUFFIX
            response = self.render(tmpfile, result, env=env, request=request, default_template=['default.html', self.default_template])
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
        
        env = self.get_execute_env(local_env)
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
        set_ini = os.path.join(self.apps_dir, 'settings.ini')
        if os.path.exists(set_ini):
            settings.append(set_ini)
        
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
                    inifile =os.path.join(get_app_dir(p), 'settings.ini')
                    if os.path.exists(inifile):
                        settings.insert(0, inifile)
           
        modules['views'] = list(views)
        modules['settings'] = settings
        return modules
    
    def install_views(self, views):
        for v in views:
            try:
                __import__(v, {}, {}, [''])
            except Exception, e:
                log.exception(e)
            
    def install_apps(self):
        for p in self.apps:
            try:
                __import__(p)
            except Exception, e:
                log.exception(e)
            
    def install_settings(self, s):
        global settings
        inifile = pkg.resource_filename('uliweb.core', 'default_settings.ini')
        s.insert(0, inifile)
        settings = Ini()
        for v in s:
            settings.read(v)
            
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
                response = None
                _clses = {}
                _inss = {}

                #middleware process request
                middlewares = settings.GLOBAL.get('MIDDLEWARE_CLASSES', [])
                s = []
                for middleware in middlewares:
                    try:
                        cls = import_func(middleware)
                        s.append((getattr(cls, 'ORDER', 500), middleware))
                    except ImportError:
                        import traceback
                        traceback.print_exc()
                        errorpage("Can't import the middleware %s" % middleware)
                    _clses[middleware] = cls
                middlewares = [v for k, v in sorted(s)]
                
                for middleware in middlewares:
                    cls = _clses[middleware]
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
            import traceback
            traceback.print_exc()
            response = self.render(e.errorpage, Storage(e.errors), request=req)
        except NotFound, e:
            response = self.not_found(req, e)
        except InternalServerError, e:
            response = self.internal_error(req, e)
        except HTTPException, e:
            response = e
        return ClosingIterator(response(environ, start_response),
                               [local_manager.cleanup])
