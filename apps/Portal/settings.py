from uliweb.core.plugin import plugin
from uliweb.i18n import ugettext_lazy as _

LANGUAGE_CODE = 'zh'
LANGUAGES = {
    'en_US':_('English'), 
    'zh_CN':_('Simplified Chinese'),
}
MIDDLEWARE_CLASSES = (
    'uliweb.i18n.middle_i18n.I18nMiddle',
)

@plugin('prepare_template_env')
def prepare_template_env(env):
    from uliweb.utils.rst import to_html
    def rst2html(filename):
        return to_html(file(env.get_file(filename)).read())
    env['rst2html'] = rst2html
    
@plugin('startup_installed')
def startup(application, config, *args):
    import os
    from uliweb.i18n import install, set_default_language
    
    localedir = ([os.path.join(application.apps_dir, '..', 'locale')] + 
        [os.path.join(application.apps_dir, appname) for appname in application.apps])
    install('uliweb', localedir)
    set_default_language(config.get('LANGUAGE_CODE'))
    
@plugin('prepare_template_env')
def prepare_template_env(env):
    from uliweb.i18n import ugettext_lazy
    env['_'] = ugettext_lazy
