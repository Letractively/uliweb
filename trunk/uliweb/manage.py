#!/usr/bin/env python
import sys, os
import logging
import types
from optparse import make_option
import uliweb
from uliweb.core.commands import Command
from uliweb.utils.common import log, check_apps_dir
        
apps_dir = 'apps'
__commands__ = {}

def get_commands():
    global __commands__
    
    def check(c):
        return ((isinstance(c, types.ClassType) or isinstance(c, types.TypeType)) and 
            issubclass(c, Command) and c is not Command)
    
    def find_mod_commands(mod):
        for name in dir(mod):
            c = getattr(mod, name)
            if check(c):
                register_command(c)
        
    def collect_commands():
        from uliweb import get_apps
        
        for f in get_apps(apps_dir):
            m = '%s.commands' % f
            try:
                mod = __import__(m, {}, {}, [''])
            except ImportError:
                continue
            
            find_mod_commands(mod)

    collect_commands()
    return __commands__
    
def register_command(kclass):
    global __commands__
    __commands__[kclass.name] = kclass
    
workpath = os.path.join(os.path.dirname(__file__), 'lib')
if workpath not in sys.path:
    sys.path.insert(0, os.path.join(workpath, 'lib'))

from uliweb.core import SimpleFrame

def install_config(apps_dir):
    from uliweb.utils import pyini
    #user can configure custom PYTHONPATH, so that uliweb can add these paths
    #to sys.path, and user can manage third party or public apps in a separate
    #directory
    config_filename = os.path.join(apps_dir, 'config.ini')
    if os.path.exists(config_filename):
        c = pyini.Ini(config_filename)
        paths = c.GLOBAL.get('PYTHONPATH', [])
        if paths:
            for p in reversed(paths):
                p = os.path.abspath(os.path.normpath(p))
                if not p in sys.path:
                    sys.path.insert(0, p)
                    
def set_log(app):
    from uliweb.utils.common import set_log_handers
    
    if app.settings.LOG:
        level = app.settings.LOG.get("level", "info").upper()
    else:
        level = 'INFO'
    handler_name = app.settings.LOG.get("handler_class", 'StreamHandler')
    handler_cls = getattr(logging, handler_name)
    arguments = app.settings.LOG.get("arguments", ())
    handler = handler_cls(*arguments)
    set_log_handers(log, [handler])
    log.setLevel(getattr(logging, level, logging.INFO))

def make_application(debug=None, apps_dir='apps', include_apps=None, debug_console=True, settings_file='settings.ini'):
    from uliweb.utils.common import sort_list
    
    if apps_dir not in sys.path:
        sys.path.insert(0, apps_dir)
        
    install_config(apps_dir)
    
    application = app = SimpleFrame.Dispatcher(apps_dir=apps_dir, include_apps=include_apps, settings_file=settings_file)
    
    #settings global application object
    uliweb.application = app
    
    #set logger level
    set_log(app)
    
    if uliweb.settings.GLOBAL.WSGI_MIDDLEWARES:
        s = sort_list(uliweb.settings.GLOBAL.WSGI_MIDDLEWARES, default=500)
        for w in reversed(s):
            if w in uliweb.settings:
                args = uliweb.settings[w].dict()
            else:
                args = None
            if args:
                klass = args.pop('CLASS', None) or args.pop('class', None)
                if not klass:
                    log.error('Error: There is no a CLASS option in this WSGI Middleware [%s].' % w)
                    continue
                modname, clsname = klass.rsplit('.', 1)
                try:
                    mod = __import__(modname, {}, {}, [''])
                    c = getattr(mod, clsname)
                    app = c(app, **args)
                except Exception, e:
                    log.exception(e)
                
    debug_flag = uliweb.settings.GLOBAL.DEBUG
    if debug or (debug is None and debug_flag):
        log.setLevel(logging.DEBUG)
        log.info(' * Loading DebuggedApplication...')
        from werkzeug.debug import DebuggedApplication
        app = DebuggedApplication(app, debug_console)
    return app

class MakeAppCommand(Command):
    name = 'makeapp'
    args = 'appname'
    help = 'Create a new app according the appname parameter.'
    check_apps_dirs = False
    
    def handle(self, options, global_options, *args):
        if not args:
            appname = ''
            while not appname:
                appname = raw_input('Please enter app name:')
        else:
            appname = args[0]
        
        ans = '-1'
        if os.path.exists(apps_dir):
            path = os.path.join(apps_dir, appname)
        else:
            path = appname
        
        if os.path.exists(path):
            while ans not in ('y', 'n'):
                ans = raw_input('The app directory has been existed, do you want to overwrite it?(y/n)[n]')
                if not ans:
                    ans = 'n'
        else:
            ans = 'y'
        if ans == 'y':
            from uliweb.utils.common import extract_dirs
            extract_dirs('uliweb', 'template_files/app', path)
register_command(MakeAppCommand)

class MakePkgCommand(Command):
    name = 'makepkg'
    args = '<pkgname1, pkgname2, ...>'
    help = 'Create new python package folders.'

    def handle(self, options, global_options, *args):
        if not args:
            while not args:
                args = raw_input('Please enter python package name:')
            args = [args]
        
        for p in args:
            if not os.path.exists(p):
                os.makedirs(p)
            initfile = os.path.join(p, '__init__.py')
            if not os.path.exists(initfile):
                f = open(initfile, 'w')
                f.close()
register_command(MakePkgCommand)

class MakeProjectCommand(Command):
    name = 'makeproject'
    help = 'Create a new project directory according the project name'
    args = 'project_name'
    check_apps_dirs = False

    def handle(self, options, global_options, *args):
        from uliweb.utils.common import extract_dirs
        
        if not args:
            project_name = ''
            while not project_name:
                project_name = raw_input('Please enter project name:')
        else:
            project_name = args[0]
        
        ans = '-1'
        if os.path.exists(project_name):
            while ans not in ('y', 'n'):
                ans = raw_input('The project directory has been existed, do you want to overwrite it?(y/n)[n]')
                if not ans:
                    ans = 'n'
        else:
            ans = 'y'
        if ans == 'y':
            extract_dirs('uliweb', 'template_files/project', project_name)
register_command(MakeProjectCommand)

class ExportStaticCommand(Command):
    name = 'exportstatic'
    help = 'Export all installed apps static directory to output directory.'
    args = 'output_directory'
    option_list = (
        make_option('-c', '--check', action='store_true', 
            help='Check if the output files or directories have conflicts.'),
    )
    has_options = True
    
    def handle(self, options, global_options, *args):
        check_apps_dir(global_options.project)

        from uliweb.utils.common import copy_dir_with_check

        if not args:
            log.error("Error: outputdir should be a directory and existed")
            sys.exit(0)
        else:
            outputdir = args[0]

        application = SimpleFrame.Dispatcher(apps_dir=global_options.project, start=False)
        apps = application.apps
        dirs = [os.path.join(SimpleFrame.get_app_dir(appname), 'static') for appname in apps]
        copy_dir_with_check(dirs, outputdir, global_options.verbose, options.check)
register_command(ExportStaticCommand)
        
class ExtractUrlsCommand(Command):
    name = 'extracturls'
    help = 'Extract all url mappings from view modules to a specified file.'
    args = ''
    
    def handle(self, options, global_options, *args):
        urlfile = 'urls.py'
        
        application = SimpleFrame.Dispatcher(apps_dir=global_options.project, use_urls=False, start=False)
        filename = os.path.join(application.apps_dir, urlfile)
        if os.path.exists(filename):
            answer = raw_input("Error: [%s] is existed already, do you want to overwrite it[Y/n]:" % urlfile)
            if answer.strip() and answer.strip.lower() != 'y':
                return
        f = file(filename, 'w')
        print >>f, "from uliweb import simple_expose\n"
        application.url_infos.sort()
        for url, kw in application.url_infos:
            endpoint = kw.pop('endpoint')
            if kw:
                s = ['%s=%r' % (k, v) for k, v in kw.items()]
                t = ', %s' % ', '.join(s)
            else:
                t = ''
            print >>f, "simple_expose(%r, %r%s)" % (url, endpoint, t)
        f.close()
        print 'urls.py has been created successfully.'
register_command(ExtractUrlsCommand)
        
class CallCommand(Command):
    name = 'call'
    help = 'Call <exefile>.py for each installed app according the command argument.'
    args = '[-a appname] exefile'
    option_list = (
        make_option('-a', dest='appname',
            help='Appname. If not provide, then will search exefile in whole project.'),
    )
    has_options = True
    
    def handle(self, options, global_options, *args):
        if not args:
            log.error("Error: There is no command module name behind call command.")
            return
        else:
            command = args[0]
            
        if not options.appname:
            from uliweb import get_apps
            apps = get_apps(apps_dir)
        else:
            apps = [options.appname]
        exe_flag = False
        for f in apps:
            m = '%s.%s' % (f, command)
            try:
                mod = __import__(m, {}, {}, [''])
                if global_options.verbose:
                    print "Importing... %s.%s" % (f, command)
                exe_flag = True
            except ImportError:
                continue
            
        if not exe_flag:
            log.error("Can't import the [%s], please check the file and try again." % command)
register_command(CallCommand)
 
def collect_files(apps_dir, apps):
    files = [os.path.join(apps_dir, 'settings.ini')]
    
    def f(path):
        for r in os.listdir(path):
            if r in ['.svn', '_svn']:
                continue
            fpath = os.path.join(path, r)
            if os.path.isdir(fpath):
                f(fpath)
            else:
                ext = os.path.splitext(fpath)[1]
                if ext in ['.py', '.ini']:
                    files.append(fpath)
    
    from uliweb import get_app_dir
    for p in apps:
        path = get_app_dir(p)
        files.append(os.path.join(path, 'config.ini'))
        files.append(os.path.join(path, 'settings.ini'))
        f(path)
    return files
        
class RunserverCommand(Command):
    name = 'runserver'
    help = 'Start a new development server.'
    args = ''
    has_options = True
    option_list = (
        make_option('-h', dest='hostname', default='localhost',
            help='Hostname or IP.'),
        make_option('-p', dest='port', type='int', default=8000,
            help='Port number.'),
        make_option('--no-reload', dest='reload', action='store_false', default=True,
            help='If auto reload the development server. Default is True.'),
        make_option('--no-debug', dest='debug', action='store_false', default=True,
            help='If auto enable debug mode. Default is True.'),
        make_option('--thread', dest='thread', action='store_true', default=False,
            help='If use thread server mode. Default is False.'),
    )
    develop = False
    
    def handle(self, options, global_options, *args):
        from werkzeug.serving import run_simple
        from uliweb import get_apps

        if self.develop:
            include_apps = ['uliweb.contrib.develop']
            app = make_application(options.debug, global_options.project, 
                        include_apps=include_apps)
        else:
            app = make_application(options.debug, global_options.project)
            include_apps = []
        extra_files = collect_files(global_options.project, get_apps(global_options.project)+include_apps)
        run_simple(options.hostname, options.port, app, options.reload, False, True,
                   extra_files, 1, options.thread, 1)
register_command(RunserverCommand)

class DevelopCommand(RunserverCommand):
    name = 'develop'
    develop = True
register_command(DevelopCommand)

class ShellCommand(Command):
    name = 'shell'
    help = 'Create a new interactive python shell environment.'
    args = ''
    has_options = True
    option_list = (
        make_option('-i', dest='ipython', default=False, action='store_true',
            help='Using ipython if exists.'),
    )
    banner = "Uliweb Command Shell"
    
    def make_shell_env(self):
        application = SimpleFrame.Dispatcher(apps_dir=apps_dir, use_urls=False, start=False)
        env = {'application':application, 'settings':application.settings}
        return env
    
    def handle(self, options, global_options, *args):
        namespace = self.make_shell_env()
        if options.ipython:
            try:
                import IPython
            except ImportError:
                pass
            else:
                sh = IPython.Shell.IPShellEmbed(banner=self.banner)
                sh(global_ns={}, local_ns=namespace)
                return
        from code import interact
        interact(self.banner, local=namespace)
register_command(ShellCommand)

def main():
    global apps_dir
    from uliweb.core.commands import execute_command_line
    
    apps_dir = os.path.join(os.getcwd(), apps_dir)
    if os.path.exists(apps_dir):
        sys.path.insert(0, apps_dir)
       
    install_config(apps_dir)
    
    from uliweb.i18n.i18ntool import I18nCommand
    register_command(I18nCommand)
    
    execute_command_line(sys.argv, get_commands(), 'uliweb')

if __name__ == '__main__':
    main()