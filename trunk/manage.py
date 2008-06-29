#!/usr/bin/env python
import sys, os

path = os.path.dirname(__file__)
sys.path.insert(0, path)
sys.path.insert(0, os.path.join(path, 'apps'))
sys.path.insert(0, os.path.join(path, 'lib'))
#sys.path.insert(0, os.path.join(path, 'uliweb'))

from werkzeug import script

apps_dir = os.path.join(path, 'apps')

def make_application():
    from uliweb.core import SimpleFrame
    application = SimpleFrame.Dispatcher(apps_dir=apps_dir)
    if application.config.DEBUG:
        from werkzeug.debug import DebuggedApplication
        application = DebuggedApplication(application)
    return application

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
        dd = os.path.join(dst, f)
        if exact:
            shutil.rmtree(dd, True)
        if not os.path.exists(dd):
            os.makedirs(dd)
        for r in os.listdir(f):
            if r in ['.svn', '_svn']:
                continue
            fpath = os.path.join(f, r)
            if os.path.isdir(fpath):
                _copy_dir([fpath], dst, verbose)
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
        outdir = os.path.join(outputdir, 'apps')
        if not os.path.exists(outdir):
            os.makedirs(outdir)
            
        for f in (os.path.join(outdir, x) for x in ['settings.py', '__init__.py']):
            if not os.path.exists(f):
                fp = file(f, 'wb')
                fp.close()
        
        dirs = [os.path.join('apps', appname)]
        _copy_dir(dirs, outputdir, verbose, exact)
        
    else:
        #copy files
        for f in ['app.yaml', 'gae_handler.py', 'manage.py', 'wsgi_handler.wsgi']:
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

    application = make_application()
    apps = application.apps
    dirs = [os.path.join('apps', appname, 'static') for appname in apps]
    _copy_dir2(dirs, outputdir, verbose, check)
    
def extracturls(urlfile='urls.py'):
    """
    Extract all url mappings from view modules to a specified file.
    """
    from uliweb.core import SimpleFrame
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

if __name__ == '__main__':
    action_runserver = script.make_runserver(make_application, use_reloader=True, 
        port=8000, use_debugger=False)
    action_makeapp = make_app
    action_export = export
    action_exportstatic = exportstatic
    #action_shell = script.make_shell(make_shell)
    #action_initdb = lambda: make_app().init_database()
    from uliweb.i18n.i18ntool import make_extract
    action_i18n = make_extract('apps')
    action_extracturls = extracturls

    script.run()
