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

from uliweb.utils.sorteddict import SortedDict
def use_tag_handler(app):
    def use(plugin, container, stack, vars, env, dirs, writer, app=app):
        from uliweb.core.SimpleFrame import get_app_dir
        
        plugin = eval(plugin, vars, env.to_dict())
        collection = env.dicts[0].get('collection', SortedDict())
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
    return use

@plugin('startup_installed')
def startup(sender):
    from uliweb.core import template
    if sender.settings.TEMPLATE.USE_TEMPLATE_TEMP_DIR:
        template.use_tempdir(sender.settings.TEMPLATE.TEMPLATE_TEMP_DIR)
    register('use', use_tag_handler(sender))

@plugin('prepare_template_env')
def prepare_template_env(sender, env):
    def cycle(*elements):
        while 1:
            for j in elements:
                yield j

    env['cycle'] = cycle
    
@plugin('get_template_tag_handlers')
def get_template_tag_handlers(sender):
    return get_handlers()

@plugin('after_render_template')
def after_render_template(sender, text, vars, env):
    from htmlmerger import merge
    collections = []
    for i in env.dicts:
        if 'collection' in i:
            collections.append(i['collection'])
    return merge(text, collections, vars, env.to_dict())