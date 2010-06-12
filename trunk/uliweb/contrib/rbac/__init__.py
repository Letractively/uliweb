from rbac import *

from uliweb.core.dispatch import bind, get

@bind('prepare_default_env')
def prepare_default_env(sender, env):
    func = permissions.ok
    env['permission'] = func
