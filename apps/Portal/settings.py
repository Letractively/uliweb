from uliweb.core.plugin import plugin
from uliweb.i18n import ugettext_lazy as _

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
)

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
    
@plugin('startup_installed')
def startup(sender):
    import os
    from uliweb.i18n import install, set_default_language, format_locale
    
    localedir = ([os.path.join(sender.apps_dir, '..', 'locale')] + 
        [os.path.join(sender.apps_dir, appname) for appname in sender.apps])
    install('uliweb', localedir)
    set_default_language(sender.config.get('LANGUAGE_CODE'))
    
    d = {}
    for k, v in sender.config.get('LANGUAGES', {}).items():
        d[format_locale(k)] = v
    sender.config['LANGUAGES'] = d
    
@plugin('prepare_template_env')
def prepare_template_env(sender, env):
    from uliweb.i18n import ugettext_lazy
    env['_'] = ugettext_lazy
