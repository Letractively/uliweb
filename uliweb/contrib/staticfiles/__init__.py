from uliweb.core.plugin import plugin
from uliweb.core.SimpleFrame import expose

@plugin('prepare_default_env')
def prepare_default_env(sender, env):
    global BUFFER_SIZE, SAVING_PATH
    
    env['url_for_static'] = url_for_static
    
    url = sender.settings.staticfiles.STATIC_URL.rstrip('/')
    expose('%s/<path:filename>' % url, static=True)(static)
    
def url_for_static(filename=None, **kwargs):
    from uliweb.core.SimpleFrame import url_for
    kwargs['filename'] = filename
    return url_for('uliweb.contrib.staticfiles.static', **kwargs)

from uliweb.core.SimpleFrame import static_serve

def static(filename):
    return static_serve(application, filename)

