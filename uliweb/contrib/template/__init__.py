import os
import re
from uliweb.core.dispatch import bind
from uliweb.utils.common import log

_template_handlers = {}
def register_tag(name, handler):
    global _template_handlers
    
    _template_handlers[name] = handler
    
def get_handlers():
    global _template_handlers
    return _template_handlers

_saved_template_plugins_modules = {}

r_with = re.compile('\s+with\s+')
def _parse_arguments(text):
    b = r_with.split(text)
    if len(b) == 1:
        name, args = b[0], ()
    else:
        name = b[0]
        args = [x.strip() for x in b[1].split(',')]
    return name, args

def eval_vars(vs, vars, env):
    if isinstance(vs, (tuple, list)):
        return [eval_vars(x, vars, env) for x in vs]
    else:
        return eval(vs, vars, env.to_dict())

from uliweb.utils.sorteddict import SortedDict
def use_tag_handler(app):
    def use(plugin, container, stack, vars, env, dirs, writer, app=app):
        from uliweb.core.SimpleFrame import get_app_dir
        
        plugin, args = _parse_arguments(plugin)
        plugin = eval_vars(plugin, vars, env)
        args = eval_vars(args, vars, env)
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
            v = register(app, vars, env, *args)
            if v:
                collection[plugin] = v
        env['collection'] = collection
    return use

@bind('startup_installed')
def startup(sender):
    from uliweb.core import template
    if sender.settings.TEMPLATE.USE_TEMPLATE_TEMP_DIR:
        template.use_tempdir(sender.settings.TEMPLATE.TEMPLATE_TEMP_DIR)
    register_tag('use', use_tag_handler(sender))

@bind('prepare_template_env')
def prepare_template_env(sender, env):
    def cycle(*elements):
        while 1:
            for j in elements:
                yield j

    env['cycle'] = cycle
    
@bind('get_template_tag_handlers')
def get_template_tag_handlers(sender):
    return get_handlers()

@bind('after_render_template')
def after_render_template(sender, text, vars, env):
    from htmlmerger import merge
    collections = []
    for i in env.dicts:
        if 'collection' in i:
            collections.append(i['collection'])
    return merge(text, collections, vars, env.to_dict())