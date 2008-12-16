from uliweb.core.plugin import plugin

@plugin('startup_installed')
def startup(sender):
    """
    @LANGUAGES
    @LANGUAGE_CODE
    """
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
