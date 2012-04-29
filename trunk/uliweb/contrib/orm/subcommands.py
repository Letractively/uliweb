import os
from optparse import make_option
from uliweb.core.commands import Command
from commands import SQLCommand

class InitCommand(SQLCommand, Command):
    name = 'init'
    help = 'Initialize a new scripts directory.'

    def handle(self, options, global_options, *args):
        from uliweb.utils.common import extract_dirs
        from uliweb.core.template import template_file
        from uliweb.manage import make_simple_application
        from uliweb import settings
        
        alembic_path = os.path.join(global_options.project, 'alembic', options.engine).replace('\\', '/')
        extract_dirs('uliweb.contrib.orm', 'templates/alembic', alembic_path, 
            verbose=global_options.verbose, replace=True)
        make_simple_application(project_dir=global_options.project,
            settings_file=global_options.settings,
            local_settings_file=global_options.local_settings)
        ini_file = os.path.join(alembic_path, 'alembic.ini')
        text = template_file(ini_file, 
            {'connection':settings.ORM.CONNECTION, 
            'engine_name':options.engine,
            'script_location':alembic_path})
        
        with open(ini_file, 'w') as f:
            f.write(text)
    
class RevisionCommand(SQLCommand, Command):
    name = 'revision'
    help = 'Create a new revision file.'
    option_list = (
        make_option('--autogenerate', dest='autogenerate', action='store_true', default=False,
            help='Populate revision script with candidate migration operations, based on comparison of database to model.'),
        make_option('-m', '--message', dest='message', help="Message string to use with 'revision'"),
    )
    check_apps = True
    has_options = True
    
    def handle(self, options, global_options, *args):
        from alembic.config import Config
        from uliweb.orm import engine_manager
        from uliweb.manage import make_simple_application
        
        app = make_simple_application(apps_dir=global_options.apps_dir, 
            settings_file=global_options.settings, local_settings_file=global_options.local_settings)

        alembic_path = os.path.join(global_options.project, 'alembic', options.engine).replace('\\', '/')
        configfile = os.path.join(alembic_path, 'alembic.ini')
        alembic_cfg = Config(configfile)
        alembic_cfg.set_main_option("sqlalchemy.url", engine_manager[options.engine].options.connection_string)
        alembic_cfg.set_main_option("engine_name", options.engine)
        alembic_cfg.set_main_option("script_location", alembic_path)
        self.do(alembic_cfg, args, options, global_options)
        
    def do(self, config, args, options, global_options):
        self.run(self.name, config, message=options.message, autogenerate=options.autogenerate)
        
    def run(self, cmd, config, *args, **kwargs):
        from alembic import command, util
        try:
            getattr(command, cmd)(config, *args, **kwargs)
        except util.CommandError, e:
            util.err(str(e))
        
class DiffCommand(RevisionCommand):
    name = 'diff'
    help = 'Create a new revision file with autogeneration.'
    check_apps = True
    has_options = True
    
    def do(self, config, args, options, global_options):
        self.run('revision', config, message=options.message, autogenerate=True)
    
class UpgradeCommand(RevisionCommand):
    name = 'upgrade'
    help = 'Upgrade to a later version.'
    option_list = (
        make_option('--sql', dest='sql', action='store_true', default=False, 
            help="Don't emit SQL to database - dump to standard output/file instead "),
        make_option('--tag', dest='tag', help="Arbitrary 'tag' name - can be used by custom env.py scripts."),
    )
    check_apps = True
    has_options = True
    
    def do(self, config, args, options, global_options):
        if not args:
            revision = 'head'
        else:
            revision = args[0]
        self.run(self.name, config, revision=revision, sql=options.sql, tag=options.tag)
