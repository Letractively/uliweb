import os
from uliweb.core.plugin import plugin
from uliweb.utils.common import log

_template_handlers = {}
def register(name, handler):
    global _template_handlers
    
    _template_handlers[name] = handler
    
def get_handlers():
    global _template_handlers
    return _template_handlers

_saved_template_plugins_modules = {}

def use_tag_handler(plugin, container, stack, vars, env, dirs, writer):
    container.add('\nuse(%s, application, _vars, _env)\n' % plugin)

def use(plugin, app, vars, env):
    from uliweb.core.SimpleFrame import get_app_dir
    from uliweb.utils.sorteddict import SortedDict
    
    collection = env.get('collection', SortedDict())
    if plugin in _saved_template_plugins_modules:
        mod = _saved_template_plugins_modules[plugin]
    else:
        from uliweb.utils.common import is_pyfile_exist
        mod = None
        for p in app.apps:
            if not is_pyfile_exist(os.path.join(get_app_dir(p), 'template_plugins'), plugin):
                continue
            module = '.'.join([p, 'template_plugins', plugin])
            try:
                mod = __import__(module, {}, {}, [''])
            except ImportError, e:
                log.exception(e)
                mod = None
        if mod:
            _saved_template_plugins_modules[plugin] = mod
    register = getattr(mod, 'register', None)
    if register:
        v = register(app, vars, env)
        if v:
            collection[plugin] = v
    env['collection'] = collection

@plugin('startup_installed')
def startup(sender):
    from uliweb.core import template
    if sender.settings.TEMPLATE.USE_TEMPLATE_TEMP_DIR:
        template.use_tempdir(sender.settings.TEMPLATE.TEMPLATE_TEMP_DIR)
    register('use', use_tag_handler)

@plugin('before_render_template')
def before_render_template(sender, env, out):
    from uliweb.utils.sorteddict import SortedDict
    env['collection'] = SortedDict()
    
@plugin('prepare_template_env')
def prepare_template_env(sender, env):
    def cycle(*elements):
        while 1:
            for j in elements:
                yield j

    env['cycle'] = cycle
    env['use'] = use
    
@plugin('get_template_tag_handlers')
def get_template_tag_handlers(sender):
    return get_handlers()

@plugin('after_render_template')
def after_render_template(sender, text, vars, env):
    from htmlmerger import merge
    return merge(text, env.get('collection', {}), vars, env)