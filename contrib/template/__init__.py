from uliweb.core.plugin import plugin

@plugin('startup_installed')
def startup(sender):
    """
    @USE_TEMPLATE_TEMP_DIR default=False
    @TEMPLATE_TEMP_DIR default='./tmp/templates_temp'
    """
    from uliweb.core import template
    if sender.settings.USE_TEMPLATE_TEMP_DIR:
        template.use_tempdir(sender.settings.get('TEMPLATE_TEMP_DIR', None))
