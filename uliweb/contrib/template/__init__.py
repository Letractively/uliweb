from uliweb.core.plugin import plugin

@plugin('startup_installed')
def startup(sender):
    from uliweb.core import template
    if sender.settings.TEMPLATE.USE_TEMPLATE_TEMP_DIR:
        template.use_tempdir(sender.settings.TEMPLATE.TEMPLATE_TEMP_DIR)

@plugin('prepare_template_env')
def prepare_template_env(sender, env):
    def cycle(*elements):
        while 1:
            for j in elements:
                yield j

    env['cycle'] = cycle    
