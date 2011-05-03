import os, sys
import datetime
from decimal import Decimal
from uliweb.core.commands import Command
from optparse import make_option
from uliweb.utils.common import log, is_pyfile_exist

def get_engine(apps_dir):
    from uliweb.core.SimpleFrame import Dispatcher
    settings = {'ORM/DEBUG_LOG':False, 'ORM/AUTO_CREATE':True}
    app = Dispatcher(apps_dir=apps_dir, start=False, default_settings=settings)
    engine = app.settings.ORM.CONNECTION
    return engine

def get_tables(apps_dir, apps=None, engine=None, import_models=False):
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
    
    if import_models:
        apps = get_apps(apps_dir)
        if apps:
            apps_list = apps
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
        
    else:
        old_models = orm.__models__.keys()
        try:
            for tablename, m in orm.__models__.iteritems():
                orm.get_model(tablename)
        except:
            print "Problems to models like:", list(set(old_models) ^ set(orm.__models__.keys()))
            raise
            
    if apps:
        tables = {}
        for tablename, m in db.metadata.tables.iteritems():
            if hasattr(m, '__appname__') and m.__appname__ in apps:
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
    con.execute(table.delete())
    filename = os.path.join(dir, name+'.txt')
    
    if not os.path.exists(filename):
        log.info("The table [%s] data is not existed." % name)
        return 
    
    f = open(filename)
    try:
        first_line = f.readline()
        fields = first_line[1:].strip().split()
        n = 1
        for line in f:
            try:
                n += 1
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
            except:
                log.error('Error: Line %d' % n)
                raise
    finally:
        f.close()

class SyncdbCommand(Command):
    name = 'syncdb'
    help = 'Sync models with database. But all models should be defined in settings.ini.'
    
    def handle(self, options, global_options, *args):
        from sqlalchemy import create_engine

        engine = get_engine(global_options.project)
        con = create_engine(engine)
        
        for name, t in get_tables(global_options.project).items():
            if global_options.verbose:
                print 'Creating %s...' % name

class ResetCommand(Command):
    name = 'reset'
    args = '<appname, appname, ...>'
    help = 'Reset the apps models(drop and recreate). If no apps, then reset the whole database.'
    check_apps = True
    
    def handle(self, options, global_options, *args):
        from sqlalchemy import create_engine

        if args:
            message = """This command will drop all tables of app [%s], are you sure to reset[Y/n]""" % ','.join(args)
        else:
            message = """This command will drop whole database, are you sure to reset[Y/n]"""
        ans = raw_input(message)
        if ans and ans.upper() != 'Y':
            print "Command be cancelled!"
            return
        
        engine = get_engine(global_options.project)
        con = create_engine(engine)
        
        for name, t in get_tables(global_options.project, args).items():
            if global_options.verbose:
                print 'Resetting %s...' % name
            t.drop(con)
            t.create(con)

class ResetTableCommand(Command):
    name = 'resettable'
    args = '<tablename, tablename, ...>'
    help = 'Reset the tables(drop and recreate). If no tables, then will do nothing.'
    
    def handle(self, options, global_options, *args):
        from sqlalchemy import create_engine
        from uliweb import orm

        if not args:
            print "Failed! You should pass one or more tables name."
            sys.exit(1)

        message = """This command will drop all tables [%s], are you sure to reset[Y/n]""" % ','.join(args)
        ans = raw_input(message)
        if ans and ans.upper() != 'Y':
            print "Command be cancelled!"
            return
        
        engine = get_engine(global_options.project)
        con = create_engine(engine)
        
        for name in args:
            m = orm.get_model(name)
            if not m:
                print "Error! Can't find the table %s...Skipped!" % name
                continue
            t = m.table
            if global_options.verbose:
                print 'Resetting %s...' % name
            t.drop(con)
            t.create(con)

class SQLCommand(Command):
    name = 'sql'
    args = '<appname, appname, ...>'
    help = 'Display the table creation sql statement. If no apps, then process the whole database.'
    check_apps = True
    
    def handle(self, options, global_options, *args):
        from sqlalchemy.schema import CreateTable
        
        for name, t in sorted(get_tables(global_options.project, args).items()):
            _t = CreateTable(t)
            print _t
            
class DumpCommand(Command):
    name = 'dump'
    args = '<appname, appname, ...>'
    help = 'Dump all models records according all available tables. If no tables, then process the whole database.'
    option_list = (
        make_option('-o', dest='output_dir', default='./data',
            help='Output the data files to this directory.'),
    )
    has_options = True
    check_apps = True
    
    def handle(self, options, global_options, *args):
        from sqlalchemy import create_engine

        if not os.path.exists(options.output_dir):
            os.makedirs(options.output_dir)
        
        engine = get_engine(global_options.project)
        con = create_engine(engine)

        for name, t in get_tables(global_options.project, args, engine=engine).items():
            if global_options.verbose:
                print 'Dumpping %s...' % name
            dump_table(name, t, options.output_dir, con)

class DumpTableCommand(Command):
    name = 'dumptable'
    args = '<tablename, tablename, ...>'
    help = 'Dump all tables records according all available apps. If no apps, then will do nothing.'
    option_list = (
        make_option('-o', dest='output_dir', default='./data',
            help='Output the data files to this directory.'),
    )
    has_options = True
    
    def handle(self, options, global_options, *args):
        from sqlalchemy import create_engine
        from uliweb import orm
        
        if not os.path.exists(options.output_dir):
            os.makedirs(options.output_dir)
        
        engine = get_engine(global_options.project)
        con = create_engine(engine)

        if not args:
            print "Failed! You should pass one or more tables name."
            sys.exit(1)
            
        for name in args:
            m = orm.get_model(name)
            if not m:
                print "Error! Can't find the table %s...Skipped!" % name
                continue
            t = m.table
            if global_options.verbose:
                print 'Dumpping %s...' % name
            dump_table(name, t, options.output_dir, con)

class LoadCommand(Command):
    name = 'load'
    args = '<appname, appname, ...>'
    help = 'Load all models records according all available apps. If no apps, then process the whole database.'
    option_list = (
        make_option('-d', dest='dir', default='./data',
            help='Directory of data files.'),
    )
    has_options = True
    check_apps = True
    
    def handle(self, options, global_options, *args):
        from uliweb import orm
        
        if args:
            message = """This command will delete all data of [%s] before loading, 
are you sure to load data[Y/n]""" % ','.join(args)
        else:
            message = """This command will delete whole database before loading, 
are you sure to load data[Y/n]"""

        ans = raw_input(message)
        if ans and ans.upper() != 'Y':
            print "Command be cancelled!"
            return

        if not os.path.exists(options.dir):
            os.makedirs(options.dir)
        
        engine = get_engine(global_options.project)
        con = orm.get_connection(engine)

        for name, t in get_tables(global_options.project, args, engine=engine).items():
            if global_options.verbose:
                print 'Loading %s...' % name
            try:
                con.begin()
                load_table(name, t, options.dir, con)
                con.commit()
            except:
                log.exception("There are something wrong when loading table [%s]" % name)
                con.rollback()

class LoadTableCommand(Command):
    name = 'loadtable'
    args = '<tablename, tablename, ...>'
    help = 'Load all tables records according all available tables. If no tables, then will no nothing.'
    option_list = (
        make_option('-d', dest='dir', default='./data',
            help='Directory of data files.'),
    )
    has_options = True
    
    def handle(self, options, global_options, *args):
        from uliweb import orm
        
        if args:
            message = """This command will delete all data of [%s] before loading, 
are you sure to load data[Y/n]""" % ','.join(args)
        else:
            print "Failed! You should pass one or more tables name."
            sys.exit(1)

        ans = raw_input(message)
        if ans and ans.upper() != 'Y':
            print "Command be cancelled!"
            return

        if not os.path.exists(options.dir):
            os.makedirs(options.dir)
        
        engine = get_engine(global_options.project)
        con = orm.get_connection(engine)

        for name in args:
            m = orm.get_model(name)
            if not m:
                print "Error! Can't find the table %s...Skipped!" % name
                continue
            t = m.table
            if global_options.verbose:
                print 'Loading %s...' % name
            try:
                con.begin()
                load_table(name, t, options.dir, con)
                con.commit()
            except:
                log.exception("There are something wrong when loading table [%s]" % name)
                con.rollback()

class DbinitdCommand(Command):
    name = 'dbinit'
    args = '<appname, appname, ...>'
    help = "Initialize database, it'll run the code in dbinit.py of each app. If no apps, then process the whole database."
    check_apps = True

    def handle(self, options, global_options, *args):
        from uliweb.core.SimpleFrame import get_apps, get_app_dir, Dispatcher
        from uliweb import orm

        app = Dispatcher(apps_dir=global_options.project, start=False)

        if not args:
            apps_list = get_apps(global_options.project)
        else:
            apps_list = args
        
        con = orm.get_connection()
        
        for p in apps_list:
            if not is_pyfile_exist(get_app_dir(p), 'dbinit'):
                continue
            m = '%s.dbinit' % p
            try:
                if global_options.verbose:
                    print "Processing %s..." % m
                con.begin()
                mod = __import__(m, {}, {}, [''])
                con.commit()
            except ImportError:
                con.rollback()
                log.exception("There are something wrong when importing module [%s]" % m)

class SqldotCommand(Command):
    name = 'sqldot'
    args = '<appname, appname, ...>'
    help = "Create graphviz dot file. If no apps, then process the whole database."
    check_apps = True
    
    def handle(self, options, global_options, *args):
        from uliweb.core.SimpleFrame import get_apps, Dispatcher
        from graph import generate_dot

        app = Dispatcher(apps_dir=global_options.project, start=False)
        if args:
            apps = args
        else:
            apps = get_apps(global_options.project)
        
        engine = get_engine(global_options.project)
        
        tables = get_tables(global_options.project, None, engine=engine)
        print generate_dot(tables, apps)
        
