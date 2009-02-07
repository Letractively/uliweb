from uliweb.core.plugin import plugin
from uliweb.core.SimpleFrame import expose

@plugin('prepare_template_env')
def prepare_template_env(sender, env):
    
    def url_for_static(filename=None, **kwargs):
        from uliweb.core.SimpleFrame import url_for
        kwargs['filename'] = filename
        return url_for('uliweb.contrib.staticfiles.views.static', **kwargs)
    
    env['url_for_static'] = url_for_static
    
    from views import static
    url = sender.settings.staticfiles.STATIC_URL.rstrip('/')
    expose('%s/<path:filename>' % url, static=True)(static)
