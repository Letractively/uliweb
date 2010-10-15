import os, sys
from uliweb.utils.common import log, check_apps_dir, is_pyfile_exist

def get_engine(apps_dir):
    from uliweb.core.SimpleFrame import Dispatcher
    settings = {'ORM/DEBUG_LOG':False, 'ORM/AUTO_CREATE':True}
    app = Dispatcher(apps_dir=apps_dir, start=False, default_settings=settings)
    engine = app.settings.ORM.CONNECTION
    return engine

def get_tables(apps_dir, appname=None, engine=None):
    from uliweb.core.SimpleFrame import get_apps, get_app_dir
    from uliweb import orm
    from sqlalchemy import create_engine
    from StringIO import StringIO
    
    if not engine:
        engine = get_engine(apps_dir)
    
    _engine = engine[:engine.find('://')+3]
    
    buf = StringIO()
    
    con = create_engine(_engine, strategy='mock', executor=lambda s, p='': buf.write(str(s) + p))
    db = orm.get_connection(con)
    
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
        if not is_pyfile_exist(get_app_dir(p), 'models'):
            continue
        m = '%s.models' % p
        try:
            mod = __import__(m, {}, {}, [''])
            models.append(mod)
        except ImportError:
            log.exception("There are something wrong when importing module [%s]" % m)
    
    if appname:
        tables = {}
        for tablename, m in orm.__models__.items():
            if m['appname'] == appname:
                tables[tablename] = db.metadata.tables[tablename]
    else:
        tables = db.metadata.tables
        
    return tables

def dump_table(name, table, dir, con, std=None):
    if not std:
        std = open(os.path.join(dir, name+'.txt'), 'w')
    else:
        std = sys.stdout
    result = con.execute(table.select())
    print >>std, '#',
    for c in table.c:
        print >>std, c.name,
    print >>std
    for r in result:
        print >>std, r
        
def load_table(name, table, dir, con):
    import datetime
    con.execute(table.delete())
    filename = os.path.join(dir, name+'.txt')
    
    if not os.path.exists(filename):
        log.info("The table [%s] data is not existed." % name)
        return 
    
    f = open(filename)
    try:
        first_line = f.readline()
        fields = first_line[1:].strip().split()
        for line in f:
            r = eval(line)
            record = dict(zip(fields, r))
            params = {}
            for c in table.c:
                if c.name in record:
                    params[c.name] = record[c.name]
#                else:
#                    params[c.name] = c.default
#                    print c.name, c.default
            
            ins = table.insert().values(**params)
            con.execute(ins)
    finally:
        f.close()

def action_syncdb(apps_dir):
    def action():
        """create all models according all available apps"""
        check_apps_dir(apps_dir)

        from uliweb.core.SimpleFrame import get_apps, get_app_dir, Dispatcher
        from uliweb import orm
        app = Dispatcher(apps_dir=apps_dir, start=False)
        orm.set_auto_create(False)
        db = orm.get_connection(app.settings.ORM.CONNECTION)
        
        models = []
        for p in get_apps(apps_dir):
            if not is_pyfile_exist(get_app_dir(p), 'models'):
                continue
            m = '%s.models' % p
            try:
                mod = __import__(m, {}, {}, [''])
                models.append(mod)
            except ImportError:
                log.exception("There are something wrong when importing module [%s]" % m)
        
        db.metadata.create_all()
            
    return action

def action_reset(apps_dir):
    def action(appname=('a', ''), verbose=('v', False)):
        """Reset the appname models(drop and recreate)"""
        from sqlalchemy import create_engine

        ans = raw_input("""This command will drop tables, are you sure to reset[Y/n]""")
        if ans and ans.upper() != 'Y':
            print "Command be cancelled!"
            return
        
        check_apps_dir(apps_dir)

        engine = get_engine(apps_dir)
        con = create_engine(engine)
        if verbose:
            con.echo = True
        
        for name, t in get_tables(apps_dir, appname).items():
            t.drop(con)
            t.create(con)
        
    return action

def action_sql(apps_dir):
    def action(appname=('a', '')):
        """Display the table creation sql statement"""
        from sqlalchemy.schema import CreateTable
        
        check_apps_dir(apps_dir)
        
        for name, t in sorted(get_tables(apps_dir, appname).items()):
            _t = CreateTable(t)
            print _t
            
    return action

def action_dump(apps_dir):
    def action(appname=('a', ''), verbose=('v', False)):
        """Dump all models records according all available apps"""
            
        from sqlalchemy import create_engine

        check_apps_dir(apps_dir)
        
        output_dir = './data'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        engine = get_engine(apps_dir)
        con = create_engine(engine)

        for name, t in get_tables(apps_dir, appname, engine=engine).items():
            dump_table(name, t, output_dir, con, std=verbose)
        
    return action

def action_load(apps_dir):
    def action(appname=('a', '')):
        """load all models records according all available apps"""
            
        from uliweb import orm
        
        ans = raw_input("""This command will delete all data of table before loading, 
are you sure to load data[Y/n]""")
        if ans and ans.upper() != 'Y':
            print "Command be cancelled!"
            return

        check_apps_dir(apps_dir)
        
        output_dir = './data'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        engine = get_engine(apps_dir)
        con = orm.get_connection(engine)

        for name, t in get_tables(apps_dir, appname, engine=engine).items():
            try:
                con.begin()
                load_table(name, t, output_dir, con)
                con.commit()
            except:
                log.exception("There are something wrong when loading table [%s]" % name)
                con.rollback()
        
    return action

def action_dbinit(apps_dir):
    def action(appname=('a', '')):
        """Initialize database, it'll run the code in dbinit.py of each app"""
        check_apps_dir(apps_dir)

        from uliweb.core.SimpleFrame import get_apps, get_app_dir, Dispatcher
        from uliweb import orm

        app = Dispatcher(apps_dir=apps_dir, start=False)

        apps = get_apps(apps_dir)
        if appname:
            apps_list = [appname]
        else:
            apps_list = apps[:]
        
        con = orm.get_connection()
        
        for p in apps_list:
            if not is_pyfile_exist(get_app_dir(p), 'dbinit'):
                continue
            m = '%s.dbinit' % p
            try:
                print "Processing %s..." % m
                con.begin()
                mod = __import__(m, {'application':app}, {}, [''])
                con.commit()
            except ImportError:
                con.rollback()
                log.exception("There are something wrong when importing module [%s]" % m)
        
    return action
