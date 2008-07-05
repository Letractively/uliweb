from uliweb.core.plugin import plugin

connection = {'connection':'sqlite:///database1.db'}
#connection = {'connection':'mysql://root:limodou@localhost/test'}

DEBUG = True
DEBUG_LOG = False

@plugin('prepare_template_env')
def prepare_template_env(sender, env):
    from uliweb.utils.textconvert import text2html
    env['text2html'] = text2html
    
@plugin('startup')
def startup(sender):
    from uliweb import orm
    orm.set_debug_query(DEBUG_LOG)
    orm.set_auto_bind(True)
    orm.set_auto_migrate(True)
    orm.get_connection(**connection)
