#!/usr/bin/env python
import sys, os
from uliweb.utils.common import log, check_apps_dir
        
apps_dir = 'apps'

workpath = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(workpath, 'lib'))

from werkzeug import script
from uliweb.core import SimpleFrame

def make_application(debug=None, apps_dir='apps', include_apps=None):
    if apps_dir not in sys.path:
        sys.path.insert(0, apps_dir)
        
    application = app = SimpleFrame.Dispatcher(apps_dir=apps_dir, include_apps=include_apps)
    debug_flag = app.settings.GLOBAL.DEBUG
#    if wrap_wsgi:
#        for p in wrap_wsgi:
#            modname, clsname = p.rsplit('.', 1)
#            mod = __import__(modname, {}, {}, [''])
#            c = getattr(mod, clsname)
#            application = c(application)
    if debug or debug_flag:
        log.info(' * Loading DebuggedApplication...')
        from werkzeug.debug import DebuggedApplication
        application = DebuggedApplication(application, True)
    return application

def make_app(appname=''):
    """create a new app according the appname parameter"""

    if not appname:
        appname = ''
        while not appname:
            appname = raw_input('Please enter app name:')
        
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

def make_project(project_name='', verbose=('v', False)):
    """create a new project directory according the project name"""
    from uliweb.utils.common import extract_dirs
    
    if not project_name:
        project_name = ''
        while not project_name:
            project_name = raw_input('Please enter project name:')

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
    
def export(outputdir=('o', ''), verbose=('v', False)):
    """
    Export Uliweb to a directory.
    """
    from uliweb.utils.common import extract_dirs
    
    if not outputdir:
        log.error("Error: outputdir can't be empty")
        sys.exit(0)

    if not os.path.exists(outputdir):
        os.makedirs(outputdir)
        
    extract_dirs('uliweb', '', outputdir, verbose)
        
def exportstatic(outputdir=('o', ''), verbose=('v', False), check=True):
    """
    Export all installed apps' static directory to outputdir directory.
    """
    check_apps_dir(apps_dir)

    from uliweb.utils.common import copy_dir_with_check

    if not outputdir:
        log.error("Error: outputdir should be a directory and can't be empty")
        sys.exit(0)

    application = make_application(False, apps_dir)
    apps = application.apps
    dirs = [os.path.join(SimpleFrame.get_app_dir(appname), 'static') for appname in apps]
    copy_dir_with_check(dirs, outputdir, verbose, check)
    
def extracturls(urlfile='urls.py'):
    """
    Extract all url mappings from view modules to a specified file.
    """
    check_apps_dir(apps_dir)

    application = SimpleFrame.Dispatcher(apps_dir=apps_dir, use_urls=False)
    filename = os.path.join(application.apps_dir, urlfile)
    if os.path.exists(filename):
        answer = raw_input("Error: [%s] is existed already, do you want to overwrite it(y/n):" % urlfile)
        if answer.strip() != 'y':
            return
    f = file(filename, 'w')
    print >>f, "from uliweb.core.rules import Mapping, add_rule\n"
    print >>f, "url_map = Mapping()"
    application.url_infos.sort()
    for url, kw in application.url_infos:
        endpoint = kw.pop('endpoint')
        if kw:
            s = ['%s=%r' % (k, v) for k, v in kw.items()]
            t = ', %s' % ', '.join(s)
        else:
            t = ''
        print >>f, "add_rule(url_map, %r, %r%s)" % (url, endpoint, t)
    f.close()

def collcet_commands():
    from uliweb.core.SimpleFrame import get_apps
    actions = {}
    for f in get_apps(apps_dir):
        m = '%s.commands' % f
        try:
            mod = __import__(m, {}, {}, [''])
        except ImportError:
            continue
        
        for t in dir(mod):
            if t.startswith('action_') and callable(getattr(mod, t)):
                actions[t] = getattr(mod, t)(apps_dir)
    return actions
                
def collect_files(apps):
    files = []
    
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
    from uliweb.core.SimpleFrame import get_app_dir
    for p in apps:
        f(get_app_dir(p))
    return files
        
def runserver(apps_dir, hostname='localhost', port=5000, use_debugger=False, 
            threaded=False, processes=1, admin=False):
    """Returns an action callback that spawns a new wsgiref server."""
    def action(hostname=('h', hostname), port=('p', port), debugger=use_debugger,
               threaded=threaded, processes=processes):
        """Start a new development server."""
        check_apps_dir(apps_dir)

        from werkzeug.serving import run_simple
        from uliweb.core.SimpleFrame import get_apps

        if admin:
            include_apps = ['uliweb.contrib.admin']
            app = make_application(use_debugger, apps_dir, 
                        include_apps=include_apps)
        else:
            app = make_application(use_debugger, apps_dir)
            include_apps = []
        extra_files = collect_files(get_apps(apps_dir)+include_apps)
        run_simple(hostname, port, app, True, debugger, True,
                   extra_files, 1, threaded, processes)
    return action

    
def main():
    global apps_dir

    apps_dir = os.path.join(os.getcwd(), apps_dir)
    if os.path.exists(apps_dir):
        sys.path.insert(0, apps_dir)
            
    action_runserver = runserver(apps_dir, port=8000, use_debugger=True)
    action_runadmin = runserver(apps_dir, port=8000, use_debugger=True, admin=True)
    action_makeapp = make_app
    action_export = export
    action_exportstatic = exportstatic
    from uliweb.i18n.i18ntool import make_extract
    action_i18n = make_extract(apps_dir)
    action_extracturls = extracturls
    action_makeproject = make_project
    
    #process app's commands.py
    locals().update(collcet_commands())

    script.run()

if __name__ == '__main__':
    main()