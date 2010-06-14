from rbac import *

from uliweb.core.dispatch import bind

@bind('prepare_default_env')
def prepare_default_env(sender, env):
    has_permission = permissions.ok
    env['has_permission'] = has_permission
    has_role = roles.has
    env['has_role'] = has_role
    
@bind('after_init_apps')
def startup(sender):
    from uliweb import settings
    
    if 'ROLE_METHODS' in settings:
        for k, v in settings.ROLE_METHODS.items():
            register_role_method(k, v)
