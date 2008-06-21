from uliweb.core.plugin import plugin

connection = {'connection':'sqlite://database.db'}
#connection = {'connection':'mysql://root:limodou@localhost/test'}

DEBUG = True
DEBUG_LOG = False

@plugin('prepare_template_env')
def prepare_template_env(sender, env):
    from uliweb.utils.textconvert import text2html
    env['text2html'] = text2html
    
@plugin('startup')
def startup(sender, config, *args):
    from uliweb import orm
    orm.set_debug_log(DEBUG_LOG)
    orm.set_auto_bind(True)
    orm.set_auto_migirate(True)
    orm.get_connection(**connection)