from uliweb.orm import get_model
from uliweb.utils.common import import_attr

__all__ = ['add_role_func', 'register_role_method',
    'superuser', 'trusted', 'anonymous']

def call_func(func, kwargs):
    import inspect
    
    args = {}
    for x in inspect.getargspec(func).args:
        try:
            args[x] = kwargs[x]
        except KeyError:
            raise Exception, "Missing args %s" % x
    return func(**args)

def superuser(user):
    return user and user.is_superuser

def trusted(user):
    return user is not None

def anonymous(user):
    return not user

__role_funcs__ = {}

def register_role_method(role_name, method):
    __role_funcs__[role_name] = method

def add_role_func(name, func):
    """
    Role_func should have 'user' parameter
    """
    global __role_funcs__
    
    __role_funcs__[name] = func
    
def has_role(user, role, **kwargs):
    if isinstance(user, (unicode, str)):
        User = get_model('user')
        user = User.get(User.c.username==user)
        
    if isinstance(role, (str, unicode)):
        Role = get_model('role')
        role = Role.get(Role.c.name==role)
    name = role.name
    
    func = __role_funcs__.get(name, None)
    if func:
        
        if isinstance(func, (unicode, str)):
            func = import_attr(func)
            
        assert callable(func)
        
        para = kwargs.copy()
        para['user'] = user
        return call_func(func, para)
    else:
        return role.users.has(user)
    
def has_permission(user, permission, **role_kwargs):
    if isinstance(user, (unicode, str)):
        User = get_model('user')
        user = User.get(User.c.username==user)
    
    flag = False
    for role in user.user_roles.all():
        if role.users.has(user):
            flag = True
            break
    return flag

