from uliweb.core.plugin import plugin
from uliweb.i18n import ugettext_lazy as _

DEBUG = True

LANGUAGE_CODE = 'zh'
LANGUAGES = {
    'en_US':_('English'), 
    'zh_CN':_('Simplified Chinese'),
}
MIDDLEWARE_CLASSES = (
    'uliweb.orm.middle_transaction.TransactionMiddle',
    'uliweb.i18n.middle_i18n.I18nMiddle',
    'uliweb.builtins.cache.middle_cache.CacheMiddle',
    'uliweb.builtins.session.middle_session.SessionMiddle',
    'uliweb.builtins.auth.middle_auth.AuthMiddle',
)

##################################################
# insert rst2html function to template environment
##################################################
@plugin('prepare_template_env')
def prepare_template_env(sender, env):
    from uliweb.utils.rst import to_html
    from uliweb.core.SimpleFrame import errorpage
    def rst2html(filename):
        f = env.get_file(filename)
        if f:
            return to_html(file(f).read())
        else:
            errorpage("Can't find the file %s" % filename)
    env['rst2html'] = rst2html
    
##################################################
# i18n initialization
##################################################
@plugin('startup_installed')
def startup(sender):
    import os
    from uliweb.i18n import install, set_default_language, format_locale
    
    localedir = ([os.path.join(sender.apps_dir, '..', 'locale')] + 
        [os.path.join(sender.apps_dir, appname) for appname in sender.apps])
    install('uliweb', localedir)
    set_default_language(sender.settings.get('LANGUAGE_CODE'))
    
    d = {}
    for k, v in sender.settings.get('LANGUAGES', {}).items():
        d[format_locale(k)] = v
    sender.settings['LANGUAGES'] = d
    
@plugin('prepare_template_env')
def prepare_template_env(sender, env):
    from uliweb.i18n import ugettext_lazy
    env['_'] = ugettext_lazy

##################################################
# set template temporarily directory
##################################################
@plugin('startup_installed')
def startup(sender):
    from uliweb.core import template
    template.use_tempdir()

##################################################
# database settings
##################################################
DEBUG_LOG = False
connection = {'connection':'sqlite:///database1.db'}
#connection = {'connection':'mysql://root:limodou@localhost/test'}

@plugin('startup')
def startup(sender):
    from uliweb import orm
    orm.set_debug_query(DEBUG_LOG)
    orm.set_auto_bind(True)
    orm.set_auto_migrate(True)
    orm.get_connection(**connection)

##################################################
# html helper initialization
##################################################
@plugin('before_render_template')
def before_render_template(sender, env, out):
    import helpers
    from uliweb.core.SimpleFrame import url_for
    from helpers import htmlwidgets
    
    helpers.before_render_template(env, out.noescape, url_for('Portal.views.static', filename=''), 
        htmlwidgets=htmlwidgets)
    
@plugin('after_render_template')
def after_render_template(sender, text, vars, env):
    import helpers
    
    return helpers.after_render_template(text, vars, env)
