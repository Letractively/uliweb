from uliweb.core.dispatch import bind
from uliweb.i18n import format_locale
from uliweb.i18n import ugettext_lazy as _

_LANGUAGES = {
    'en_US':_('English'), 
    'zh_CN':_('Simplified Chinese'),
}
LANGUAGES = {}
for k, v in _LANGUAGES.items():
    LANGUAGES[format_locale(k)] = v

@bind('startup_installed')
def startup(sender):
    """
    @LANGUAGE_CODE
    """
    import os
    from uliweb.i18n import install, set_default_language
    
    localedir = ([os.path.join(sender.apps_dir, '..', 'locale')] + 
        [os.path.join(sender.apps_dir, appname) for appname in sender.apps])
    install('uliweb', localedir)
    set_default_language(sender.settings.I18N.LANGUAGE_CODE)
    
@bind('prepare_template_env')
def prepare_template_env(sender, env):
    from uliweb.i18n import ugettext_lazy
    env['_'] = ugettext_lazy
