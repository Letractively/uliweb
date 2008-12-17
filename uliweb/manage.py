#!/usr/bin/env python
import sys, os

apps_dir = 'apps'

workpath = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(workpath, 'lib'))

from werkzeug import script
from uliweb.core import SimpleFrame

def make_application(debug=None, apps_dir='apps', wrap_wsgi=None):
    application = app = SimpleFrame.Dispatcher(apps_dir=apps_dir)
    debug_flag = app.settings.DEBUG
    if wrap_wsgi:
        for p in wrap_wsgi:
            modname, clsname = p.rsplit('.', 1)
            mod = __import__(modname, {}, {}, [''])
            c = getattr(mod, clsname)
            application = c(application)
#    from uliweb.wsgi.profile import ProfileApplication
#    application = ProfileApplication(app)
    if debug or (debug is None and debug_flag):
        print ' * Loading DebuggedApplication...'
        from werkzeug.debug import DebuggedApplication
        application = DebuggedApplication(application)
    return application

def _make_application(debug=None, apps_dir='apps', wrap_wsgi=None):
    def action():
        return make_application(debug=debug, apps_dir=apps_dir, wrap_wsgi=wrap_wsgi)
    return action

def make_app(appname=''):
    """create a new app according the appname parameter"""
    path = os.path.join(apps_dir, appname)
    
    for d in [path, os.path.join(path, 'templates'), os.path.join(path, 'static')]:
        if not os.path.exists(d):
            os.makedirs(d)

    for f in (os.path.join(path, x) for x in ['../settings.py', '../__init__.py', '__init__.py', 'settings.py', 'views.py']):
        if not os.path.exists(f):
            fp = file(f, 'wb')
            if f.endswith('views.py'):
                print >>fp, "#coding=utf-8"
                print >>fp, "from uliweb.core.SimpleFrame import expose\n"
                print >>fp, "@expose('/')"
                print >>fp, """def index():
    return '<h1>Hello, Uliweb</h1>'"""
            elif f.endswith('../settings.py'):
                print >>fp, "DEBUG = True"
            fp.close()

#copy dirs
def _copy_dir(d, dst, verbose, exact=False):
    import shutil

    for f in d:
        if not os.path.exists(f):
            if verbose:
                sys.stderr.write("Warn : %s does not exist, SKIP\n" % f)
            continue
        dd = os.path.join(dst, os.path.basename(f))
        if exact:
            shutil.rmtree(dd, True)
        if not os.path.exists(dd):
            os.makedirs(dd)
        for r in os.listdir(f):
            if r in ['.svn', '_svn']:
                continue
            fpath = os.path.join(f, r)
            if os.path.isdir(fpath):
                _copy_dir([fpath], dd, verbose)
            else:
                ext = os.path.splitext(fpath)[1]
                if ext in ['.pyc', '.pyo', '.bak', '.tmp']:
                    continue
                if verbose:
                    sys.stdout.write("Info : Copying %s to %s...\n" % (fpath, dd))
                shutil.copy2(fpath, dd)
            
            
def export(outputdir=('o', ''), verbose=('v', False), exact=('e', False), appname=('a', '')):
    """
    Export Uliweb to a directory.
    """
    import shutil
    
    if not outputdir:
        sys.stderr.write("Error: outputdir should be a directory and can't be empty")
        sys.exit(0)

    if not os.path.exists(outputdir):
        os.makedirs(outputdir)
        
    if appname:
        if not os.path.exists(outputdir):
            os.makedirs(outputdir)
            
        for f in (os.path.join(outputdir, x) for x in ['settings.py', '__init__.py']):
            if not os.path.exists(f):
                fp = file(f, 'wb')
                fp.close()
        
        dirs = [SimpleFrame.get_app_dir(appname)]
        _copy_dir(dirs, outputdir, verbose, exact)
        
    else:
        #copy files
        for f in ['app.yaml', 'gae_handler.py', 'manage.py', 'wsgi_handler.wsgi', 'runcgi.py', 'COPYLEFT.txt']:
            path = os.path.join(outputdir, f)
            if f == 'app.yaml':
                if not os.path.exists(path):
                    shutil.copy2(f, path)
            else:
                shutil.copy2(f, path)
            
        dirs = ['uliweb', 'lib']
        _copy_dir(dirs, outputdir, verbose, exact)
        
def _copy_dir2(d, dst, verbose=False, check=True):
    import shutil
    
    def _md5(filename):
        import md5
        a = md5.new()
        a.update(file(filename, 'rb').read())
        return a.digest()

    for f in d:
        if not os.path.exists(f):
            if verbose:
                sys.stderr.write("Warn : %s does not exist, SKIP\n" % f)
            continue
        if verbose:
            sys.stdout.write("Info : Processing %s...\n" % f)
        for r in os.listdir(f):
            if r in ['.svn', '_svn']:
                continue
            fpath = os.path.join(f, r)
            if os.path.isdir(fpath):
                dd = os.path.join(dst, r)
                if not os.path.exists(dd):
                    os.makedirs(dd)
                _copy_dir([fpath], dd, verbose, check)
            else:
                ext = os.path.splitext(fpath)[1]
                if ext in ['.pyc', '.pyo', '.bak', '.tmp']:
                    continue
                if check:
                    df = os.path.join(dst, r)
                    if os.path.exists(df):
                        a = _md5(fpath)
                        b = _md5(df)
                        if a != b:
                            sys.stderr.write("Error: Target file [%s] is already existed, and "
                                "it not same as source one [%s], so copy failed" % (fpath, dst))
                    else:
                        shutil.copy2(fpath, dst)
                else:
                    shutil.copy2(fpath, dst)

def exportstatic(outputdir=('o', ''), verbose=('v', False), check=True):
    """
    Export all installed apps' static directory to outputdir directory.
    """
    if not outputdir:
        sys.stderr.write("Error: outputdir should be a directory and can't be empty")
        sys.exit(0)

    application = make_application(False, apps_dir)
    apps = application.apps
    dirs = [os.path.join(SimpleFrame.get_app_dir(appname), 'static') for appname in apps]
    _copy_dir2(dirs, outputdir, verbose, check)
    
def extracturls(urlfile='urls.py'):
    """
    Extract all url mappings from view modules to a specified file.
    """
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

#def make_shell():
#    from shorty import models, utils
#    application = make_app()
#    return locals()

def collcet_commands():
    def get_apps():
        try:
            import settings
            if hasattr(settings, 'INSTALLED_APPS'):
                return getattr(settings, 'INSTALLED_APPS')
        except ImportError:
            pass
        
        s = []
        if not os.path.exists(apps_dir):
            return s
        for p in os.listdir(apps_dir):
            path = os.path.join(apps_dir, p)
            if not os.path.exists(path):
                continue
            if os.path.isdir(path) and p not in ['.svn', 'CVS'] and not p.startswith('.') and not p.startswith('_'):
                s.append(p)
        return s
    
    for f in get_apps():
        m = '%s.commands' % f
        try:
            mod = __import__(m, {}, {}, [''])
        except ImportError:
            continue
        for t in dir(mod):
            if t.startswith('action_') and callable(getattr(mod, t)):
                globals()[t] = getattr(mod, t)

def main():
    global apps_dir
    s = os.path.basename(sys.argv[0])
    prompt = """usage: %s [-d project_directory] <action> [<options>]
       %s --help""" % ('uliweb', 'uliweb')

    args = None
    if len(sys.argv) > 2 and sys.argv[1] == '-d':
        args = sys.argv[3:]
        try:
            apps_dir = sys.argv[2]
            if not os.path.exists(apps_dir):
                print ' Error: the project directory [%s] is not existed' % apps_dir
                sys.exit(1)
            sys.path.insert(0, os.path.join(apps_dir))
        except:
            import traceback
            traceback.print_exc()
            args = ['-h']
            
    else:
        if not os.path.exists(apps_dir):
            print ' Error: the project directory [%s] is not existed' % apps_dir
            sys.exit(1)
        sys.path.insert(0, os.path.join(apps_dir))
        
    print ' * APPS_DIR =',  apps_dir
    
    action_runserver = script.make_runserver(_make_application(None, apps_dir), 
        port=8000, use_reloader=True, use_debugger=True)
    action_makeapp = make_app
    action_export = export
    action_exportstatic = exportstatic
    from uliweb.i18n.i18ntool import make_extract
    action_i18n = make_extract('apps')
    action_extracturls = extracturls
    
    #process app's commands.py
    collcet_commands()

    script.run(args=args, prompt=prompt)

if __name__ == '__main__':
    main()