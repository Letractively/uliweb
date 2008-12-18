from uliweb.core.plugin import plugin
from uliweb.i18n import ugettext_lazy as _

DEBUG = True

LANGUAGE_CODE = 'zh'
LANGUAGES = {
    'en_US':_('English'), 
    'zh_CN':_('Simplified Chinese'),
}

MIDDLEWARE_CLASSES = (
#    'uliweb.orm.middle_transaction.TransactionMiddle',
    'uliweb.i18n.middle_i18n.I18nMiddle',
#    'uliweb.contrib.cache.middle_cache.CacheMiddle',
#    'uliweb.contrib.session.middle_session.SessionMiddle',
#    'uliweb.contrib.auth.middle_auth.AuthMiddle',
)

USE_TEMPLATE_TEMP_DIR = False

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
# database settings
##################################################
ORM_DEBUG_LOG = False
ORM_CONNECTION = {'connection':'sqlite:///database1.db'}
#connection = {'connection':'mysql://root:limodou@localhost/test'}

##################################################
# html helper initialization
##################################################
STATIC_SUFFIX = '/static/'
