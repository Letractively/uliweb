from uliweb.core.plugin import plugin

LANGUAGE_CODE = 'zh'

@plugin('prepare_template_env')
def prepare_template_env(env):
    from uliweb.utils.rst import to_html
    def rst2html(filename):
        return to_html(file(env.get_file(filename)).read())
    env['rst2html'] = rst2html
    
@plugin('startup_installed')
def startup(application, config, *args):
    import os
    from uliweb.core.i18n import install, set_default_language
    
    localedir = (#[os.path.join(application.apps_dir, '..', 'locale')] + 
        [os.path.join(application.apps_dir, appname) for appname in application.apps])
    install('uliweb', localedir)
    set_default_language(config.get('LANGUAGE_CODE'))
    
@plugin('prepare_template_env')
def prepare_template_env(env):
    from uliweb.core.i18n import ugettext_lazy
    env['_'] = ugettext_lazy
