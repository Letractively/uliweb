from uliweb.core.dispatch import bind, get
from uliweb.core.SimpleFrame import expose

@bind('prepare_template_env')
def prepare_template_env(sender, env):
    env['url_for_static'] = url_for_static
    
    url = sender.settings.wsgi_middleware_staticfiles.STATIC_URL.rstrip('/')
    expose('%s/<path:filename>' % url, static=True)(static)
    
def url_for_static(filename=None, **kwargs):
    from uliweb.core.SimpleFrame import url_for, local
    filename = get(local.application, 'url_for_static_filename', filename, kwargs) or filename
    kwargs['filename'] = filename
    return url_for('uliweb.contrib.staticfiles.static', **kwargs)

from uliweb.core.SimpleFrame import static_serve

def static(filename):
    return static_serve(application, filename, dir=application.settings.STATICFILES.STATIC_FOLDER)

