import os
from uliweb.utils.common import log, check_apps_dir

def action_syncdb(apps_dir):
    def action():
        """create all models according all available apps"""
        check_apps_dir(apps_dir)

        from uliweb.core.SimpleFrame import get_apps, get_app_dir, Dispatcher
        from uliweb import orm
        app = Dispatcher(apps_dir=apps_dir, start=False)
        orm.set_auto_bind(True)
        orm.set_auto_create(False)
        db = orm.get_connection(app.settings.ORM.CONNECTION)
        
        models = []
        for p in get_apps(apps_dir):
            path = os.path.join(get_app_dir(p), 'models.py')
            if not os.path.exists(path):
                path = os.path.join(get_app_dir(p), 'models.pyc')
                if not os.path.exists(path):
                    path = os.path.join(get_app_dir(p), 'models.pyc')
                    if not os.path.exists(path):
                        continue
            m = '%s.models' % p
            try:
                mod = __import__(m, {}, {}, [''])
                models.append(mod)
            except ImportError:
                log.exception()
        
        db.metadata.create_all()
            
    return action

def action_reset(apps_dir):
    def action(appname=''):
        """Reset the appname models(drop and recreate)"""
        check_apps_dir(apps_dir)

        if not appname:
            appname = ''
            while not appname:
                appname = raw_input('Please enter app name:')
        
        from uliweb.core.SimpleFrame import get_app_dir, Dispatcher
        from uliweb import orm
        app = Dispatcher(apps_dir=apps_dir, start=False)
        orm.set_auto_bind(True)
        orm.set_auto_create(False)
#        orm.set_debug_query(True)
        db = orm.get_connection(app.settings.ORM.CONNECTION)

        path = os.path.join(get_app_dir(appname), 'models.py')
        if not os.path.exists(path):
            path = os.path.join(get_app_dir(appname), 'models.pyc')
            if not os.path.exists(path):
                path = os.path.join(get_app_dir(appname), 'models.pyc')
                if not os.path.exists(path):
                    return
        m = '%s.models' % appname
        try:
            mod = __import__(m, {}, {}, [''])
        except ImportError:
            log.exception()
        
        db.metadata.drop_all()
        db.metadata.create_all()
            
    return action

def action_sql(apps_dir):
    def action(appname=''):
        """Display the table creation sql statement"""
        check_apps_dir(apps_dir)
        
        from uliweb.core.SimpleFrame import get_apps, get_app_dir, Dispatcher
        from uliweb import orm
        
        app = Dispatcher(apps_dir=apps_dir, start=False)
        orm.set_auto_bind(True)
        orm.set_auto_create(False)
        db = orm.get_connection(app.settings.ORM.CONNECTION)

        from StringIO import StringIO
        from sqlalchemy import create_engine
        
        buf = StringIO()
        p = app.settings.ORM.CONNECTION
        _engine = p[:p.find('://')+3]
        db = create_engine(_engine, strategy='mock', executor=lambda s, p='': buf.write(s + p))
        orm.set_connection(db, debug=True)
        
        apps = get_apps(apps_dir)
        if appname:
            apps_list = [appname]
        else:
            apps_list = apps[:]
        models = []
        for p in apps_list:
            if p not in apps:
                log.error('Error: Appname %s is not a valid app' % p)
                continue
            path = os.path.join(get_app_dir(p), 'models.py')
            if not os.path.exists(path):
                path = os.path.join(get_app_dir(p), 'models.pyc')
                if not os.path.exists(path):
                    path = os.path.join(get_app_dir(p), 'models.pyc')
                    if not os.path.exists(path):
                        continue
            m = '%s.models' % p
            try:
                mod = __import__(m, {}, {}, [''])
                models.append(mod)
            except ImportError:
                log.exception()
        
        db.metadata.create_all(db)
        print buf.getvalue()
    return action
