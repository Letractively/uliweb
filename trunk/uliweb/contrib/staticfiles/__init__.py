from uliweb.core.plugin import plugin

@plugin('prepare_template_env')
def prepare_template_env(sender, env):
    
    def url_for_static(filename=None, **kwargs):
        from uliweb.core.SimpleFrame import url_for
        kwargs['filename'] = filename
        return url_for('uliweb.contrib.staticfiles.views.static', **kwargs)
    
    env['url_for_static'] = url_for_static
    
    from views import static

    expose('%s/<path:filename>' % sender.settings.GLOBAL.STATIC_MEDIA, static=True)(static)
