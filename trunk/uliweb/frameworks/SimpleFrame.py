####################################################################
# Author: Limodou@gmail.com
# License: GPLv2
####################################################################

#defautl global settings
import os
from webob import Request, Response
#from werkzeug import Request, Response
from werkzeug import ClosingIterator
from werkzeug.exceptions import HTTPException, NotFound, InternalServerError
from werkzeug.routing import RequestRedirect

from werkzeug import Local, LocalManager
from werkzeug.routing import Map, Rule
from utils.template import template_file, get_templatefile
from utils.storage import Storage
from utils.plugin import *

APPS_DIR = 'apps'

local = Local()
local_manager = LocalManager([local])

from werkzeug.routing import BaseConverter
class RegexConverter(BaseConverter):
    """
    Matches regular expression::

        Rule('/<regex("pattern"):argu_name>')
    """

    def __init__(self, map, *items):
        BaseConverter.__init__(self, map)
        self.regex = items[0]

url_map = Map(converters={'regex':RegexConverter})
config = None

def expose(rule=None, **kw):
    """
    add a url assigned to the function to url_map, if rule is None, then
    the url will be function name, for example:
        
        @expose
        def index(req):
            
        will be url_map.add('index', index)
    """
    if callable(rule):
        f = rule
        import inspect
        args = inspect.getargspec(f)[0]
        if args :
            args = ['<%s>' % x for x in args]
        appname = f.__module__.split('.')[1]
        rule = '/' + '/'.join([appname, f.__name__] + args)
        kw['endpoint'] = f.__module__ + '.' + f.__name__
        url_map.add(Rule(rule, **kw))
        return f
        
    def decorate(f):
        kw['endpoint'] = f.__module__ + '.' + f.__name__
        url_map.add(Rule(rule, **kw))
        return f
    return decorate

def url_for(endpoint, _external=False, **values):
    dir = os.path.basename(APPS_DIR)
    if not endpoint.startswith(dir + '.'):
        endpoint = dir + '.' + endpoint
    return local.url_adapter.build(endpoint, values, force_external=_external)

def import_func(path):
    module, func = path.rsplit('.', 1)
    mod = __import__(module, {}, {}, [''])
    return getattr(mod, func)

class HTTPError(Exception):
    def __init__(self, errorpage=None, **kwargs):
        self.errorpage = errorpage or config.ERROR_PAGE
        self.errors = kwargs

    def __str__(self):
        return self.e
    
def redirect(url):
    raise RequestRedirect(url)

def errorpage(request, message='', errorpage=None, **kwargs):
    kwargs.setdefault('message', message)
    kwargs.setdefault('link', request.path_info)
    raise HTTPError(errorpage, **kwargs)

def static_serve(request, filename):
    for p in request.application.apps:
        f = os.path.join(APPS_DIR, p, 'static', filename)
        if os.path.exists(f):
            from utils.FileApp import return_file
            return return_file(f)
    raise NotFound()

class Dispatcher(object):
    installed = False
    def __init__(self, apps_dir=APPS_DIR):
        if not Dispatcher.installed:
            self.init(apps_dir)
        
    def init(self, apps_dir):
        import __builtin__
        setattr(__builtin__, 'expose', expose)
        setattr(__builtin__, 'plugin', plugin)
        
        APPS_DIR = apps_dir
        Dispatcher.apps_dir = apps_dir
        Dispatcher.modules = self.collect_modules()
        self.install_settings(self.modules['settings'])
        Dispatcher.apps = self.modules['apps']
        self.install_views(self.modules['views'])
        Dispatcher.template_dirs = self.get_template_dirs()
        Dispatcher.env = self._prepare_env()
        Dispatcher.template_env = Dispatcher.env.copy()
        callplugin('prepare_default_env', Dispatcher.env)
        callplugin('prepare_template_env', Dispatcher.template_env)
        Dispatcher.installed = True
        
    def _prepare_env(self):
        env = {}
        env['url_for'] = url_for
        env['redirect'] = redirect
        env['error'] = errorpage
        env['url_map'] = url_map
        env['render'] = self.render
        env['config'] = config
        from werkzeug import html, xhtml
        env['html'] = html
        env['xhtml'] = xhtml
        from utils import Form
        env['Form'] = Form
        return env
        
    def render(self, templatefile, vars, env=None, dirs=None):
        dirs = dirs or self.template_dirs
        env = self.get_template_env(env)
        return Response(template_file(templatefile, vars, env, dirs), content_type='text/html')
    
    def not_found(self, request, e):
        tmp_file = get_templatefile('404'+config.TEMPLATE_SUFFIX, self.template_dirs)
        if tmp_file:
            response = self.render(tmp_file, {'url':request.path})
        else:
            response = e
        return response
    
    def internal_error(self, request, e):
        tmp_file = get_templatefile('500'+config.TEMPLATE_SUFFIX, self.template_dirs)
        if tmp_file:
            response = self.render(tmp_file, {'url':request.path})
        else:
            response = e
        return response
    
    def get_template_env(self, env=None):
        e = self.template_env
        if env:
            e.update(env)
        return e
    
    def call_handler(self, handler, request, response=None, **values):
        response = response or Response(content_type='text/html')
        request.appname = handler.__module__.split('.')[1]
        request.function = handler.__name__
        request.application = self
        if not handler.func_globals.get('__bounded__', False):
            for k, v in self.env.iteritems():
                handler.func_globals[k] = v
            handler.func_globals['__bounded__'] = True
        
        #prepare local env
        local_env = {}
        local_env['application'] = self
        local_env['request'] = request
        local_env['response'] = response
        
        for k, v in local_env.iteritems():
            handler.func_globals[k] = v
        
        env = self.get_template_env(local_env)
        handler.func_globals['env'] = env
        
        result = handler(**values)
        if isinstance(result, dict):
            result = Storage(result)
            if hasattr(response, 'view') and response.view:
                tmpfile = response.view
            else:
                tmpfile = request.function + config.TEMPLATE_SUFFIX
            dirs = [os.path.join(self.apps_dir, request.appname, 'templates')] + self.template_dirs
            response = self.render(tmpfile, result, env=env)
        elif isinstance(result, (str, unicode)):
            response = Response(result, content_type='text/html')
        elif isinstance(result, Response):
            response = result
        else:
            response = Response(str(result), content_type='text/html')
        return response
            
    def collect_modules(self):
        modules = {}
        views = set()
        settings = []
        apps = []
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
                        views.add('.'.join([os.path.basename(self.apps_dir), appname, subfolder, fname]))
                    else:
                        views.add('.'.join([os.path.basename(self.apps_dir), appname, fname]))
            
        for p in os.listdir(self.apps_dir):
            path = os.path.join(self.apps_dir, p)
            if p.startswith('.') or p.startswith('_') or p.startswith('CVS'):
                continue
            if os.path.isdir(path):
                #deal with views
                views_path = os.path.join(p, 'views')
                if os.path.exists(views_path) and os.path.isdir(views_path):
                    enum_views(views_path, p, 'views')
                else:
                    enum_views(path, p, pattern='views*')
                #deal with settings
                settings_files = ['.'.join([os.path.basename(self.apps_dir), p, 'settings']) for x in ['.py', '.pyc', '.pyo']
                    if os.path.exists(os.path.join(os.path.basename(self.apps_dir), p, 'settings%s' % x))]
                if settings_files:
                    settings.append(settings_files[0])
                apps.append(p)
           
        modules['views'] = list(views)
        modules['settings'] = settings
        modules['apps'] = apps
        return modules
    
    def install_views(self, views):
        for v in views:
            appname = v.rsplit('.')[-2]
            if appname in self.apps:
                __import__(v, {}, {}, [''])
            
    def install_settings(self, s):
        global config
        s.insert(0, 'frameworks.default_config')
        config = Storage({})
        for v in s:
            mod = __import__(v, {}, {}, [''])
            if not getattr(mod, 'APP_VALID', True):
                appname = v.rsplit('.')[-2]
                if appname in self.modules['apps']:
                    self.modules['apps'].remove(appname)
                continue
            for k in dir(mod):
                if k.startswith('_') or not k.isupper() or k == 'APP_VALID':
                    pass
                else:
                    config[k] = getattr(mod, k)
            
    def get_template_dirs(self):
        template_dirs = [os.path.join(self.apps_dir, p, 'templates') for p in self.apps]
        return template_dirs
    
    def __call__(self, environ, start_response):
        local.application = self
        req = Request(environ)
        res = Response(content_type='text/html')
        local.url_adapter = adapter = url_map.bind_to_environ(environ)
        try:
            endpoint, values = adapter.match()
            for v in self.modules['views']:
                if endpoint.startswith(v):
                    break
            else:
                raise NotFound()
            handler = import_func(endpoint)
            #wrap the handler, add some magic object to func_globals
            response = self.call_handler(handler, req, res, **values)
        except RequestRedirect, e:
            response = e
        except HTTPError, e:
            response = self.render(e.errorpage, Storage(e.errors))
        except NotFound, e:
            response = self.not_found(req, e)
        except InternalServerError, e:
            response = self.internal_error(req, e)
        except HTTPException, e:
            response = e
        return ClosingIterator(response(environ, start_response),
                               [local_manager.cleanup])
