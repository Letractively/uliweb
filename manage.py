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
        
#def make_shell():
#    from shorty import models, utils
#    application = make_app()
#    return locals()

if __name__ == '__main__':
    action_runserver = script.make_runserver(make_application, use_reloader=True, 
        port=8000, use_debugger=True)
    action_makeapp = make_app
    #action_shell = script.make_shell(make_shell)
    #action_initdb = lambda: make_app().init_database()

    script.run()
