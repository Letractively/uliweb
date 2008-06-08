#!/usr/bin/env python
import sys, os

sys.path.insert(0, 'apps')
sys.path.insert(0, 'uliweb')

from werkzeug import script

apps_dir = os.path.join(os.path.dirname(__file__), 'apps')

def make_application():
    from frameworks import SimpleFrame
    return SimpleFrame.Dispatcher(apps_dir=apps_dir)

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
                print >>fp, "from frameworks.SimpleFrame import expose"
            fp.close()
            
def export(outputdir=''):
    """
    Export Uliweb to a directory.
    """
    import shutil
    
    if not outputdir:
        sys.stderr.write("Error: outputdir should be a directory and can't be empty")
        sys.exit(0)
        
    if not os.path.exists(outputdir):
        os.makedirs(outputdir)
        
    #copy files
    for f in ['app.yaml', 'gae_handler.py', 'manage.py']:
        path = os.path.join(outputdir, f)
        if f == 'app.yaml':
            if not os.path.exists(path):
                shutil.copy2(f, path)
        else:
            shutil.copy2(f, path)
        
    #copy dirs
    def copy_dir(d, dst):
        for f in d:
            dd = os.path.join(dst, f)
            if not os.path.exists(dd):
                os.makedirs(dd)
            for r in os.listdir(f):
                if r in ['.svn']:
                    continue
                fpath = os.path.join(f, r)
                if os.path.isdir(fpath):
                    copy_dir([fpath], dst)
                else:
                    ext = os.path.splitext(fpath)[1]
                    if ext in ['.pyc', '.pyo', '.bak', '.tmp']:
                        continue
                    shutil.copy2(fpath, dd)
    
    copy_dir(['uliweb'], outputdir)
        
#def make_shell():
#    from shorty import models, utils
#    application = make_app()
#    return locals()

if __name__ == '__main__':
    action_runserver = script.make_runserver(make_application, use_reloader=True, 
        port=8000, use_debugger=True)
    action_makeapp = make_app
    action_export = export
    #action_shell = script.make_shell(make_shell)
    #action_initdb = lambda: make_app().init_database()

    script.run()
