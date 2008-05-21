#!/usr/bin/env python
import sys, os
sys.path.insert(0, 'apps')
sys.path.insert(0, 'uliweb')

from werkzeug import script

def make_app():
    from frameworks import SimpleFrame
    apps_dir = os.path.join(os.path.dirname(__file__), 'apps')
    return SimpleFrame.Dispatcher(apps_dir=apps_dir)

#def make_shell():
#    from shorty import models, utils
#    application = make_app()
#    return locals()

if __name__ == '__main__':
    action_runserver = script.make_runserver(make_app, use_reloader=True, 
        port=8000, use_debugger=True)
    #action_shell = script.make_shell(make_shell)
    #action_initdb = lambda: make_app().init_database()

    script.run()
