from uliweb.orm import get_model

__all__ = ['PermissionError', 'RoleError', 'Role', 'RoleManager', 'roles', 'permissions',
    'PermissionManager', 'Permission', 'add_role_func', 'register_role_method',
    'superuser', 'trusted', 'anonymous', 'owner']

class PermissionError(Exception): pass
class RoleError(Exception): pass

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

def owner(user, obj):
    """
    If you want to use it, you should define "owner" function to object
    """
    if hasattr(obj, 'owner'):
        return obj.owner(user)
    else:
        return False

__role_funcs__ = {}

def register_role_method(role_name, method):
    __role_funcs__[role_name] = method

def add_role_func(name, func):
    global __role_funcs__
    
    __role_funcs__[name] = func

class Role(object):
    def __init__(self, name, description, users=[], reserve=False, record=None, loaded=False):
        self.name = name
        self.description = description
        self.users = users
        self.reserve = reserve
        self.loaded = loaded
        self.record = record #used to save underlying Role object
        
    def get_record(self):
        self.load()
        return self.record
        
    def get_users_name(self, check=True):
        self.load(check)

        r = []
        for x in self.users:
            if isinstance(x, (unicode, str)):
                r.append(x)
            else:
                #here x should be instance of Modal
                r.append(x.name)
        return r
    
    def get_users(self, check=True):
        self.load(check)

        for i, x in enumerate(self.users):
            if isinstance(x, (unicode, str)):
                User = get_model('user')
                user = User.get(User.c.username==x)
                self.users[i] = user
        self.users = filter(None, self.users)
        return self.users
        
    def save(self):
        RoleModel = get_model('role')
        r = RoleModel.get(RoleModel.c.name==self.name)
        if r:
            r.description = self.description
            #don't save reserve field again
            r.save()
        else:
            r = RoleModel(name=self.name, description=self.description, reserve=self.reserve)
            r.save()
            
        r.users.clear()
        for u in self.get_users(False):
            r.users.add(u)
        self.record = r
        
    def load(self, check=True):
        if not check:
            return
        if not self.loaded:
            RoleModel = get_model('role')
            r = RoleModel.get(RoleModel.c.name==self.name)
            if r:
                self.record = r
                self.description = r.description
                self.reserve = r.reserve
                self.users = list(r.users.all())
                self.loaded = True
        
    def has(self, user, **kwargs):
        """
        user should be User's instance.
        """
        global __role_funcs__
        self.load()
        
        if isinstance(user, (unicode, str)):
            User = get_model('user')
            user = User.get(User.c.username==user)
            
        if not user:
            return False
            
        func = __role_funcs__.get(self.name, None)
        if func:
            from uliweb.utils.common import import_attr
            
            if isinstance(func, (unicode, str)):
                func = import_attr(func)
                
            assert callable(func)
            
            env = kwargs.copy()
            env['user'] = user
            if not callable(func):
                raise Exception, "Func %r should be callable." % func
            return call_func(func, env)
        else:
            return user.username in self.get_users_name()
        
    def __repr__(self):
        return "<%s 'name':%r>" % (self.__class__.__name__, self.name)
        
class RoleManager(object):
    def __init__(self):
        self.roles = {}
        
    def add(self, name, description, users=[], reserve=False, record=None, loaded=False):
        r = self.roles[name] = Role(name, description, users, reserve, record, loaded)
        return r
        
    def load(self):
        RoleModel = get_model('role')
        for r in RoleModel.all():
            self.roles[r.name] = Role(r.name, r.description, reverse=False)
        
    def get(self, role):
        if isinstance(role, (unicode, str)):
            if role in self.roles:
                return self.roles[role]
            else:
                RoleModel = get_model('role')
                r = RoleModel.get(RoleModel.c.name==role)
                if r:
                    return self.add(r.name, r.description, users=list(r.users.all()), record=r, loaded=True)
                else:
                    raise RoleError, "Role [%s] is not existed!" % role
        elif isinstance(role, Role):
            return role
        else:
            return self.add(role.name, role.description, users=list(role.users.all()), record=role, loaded=True)
            
    def has(self, role, user, **kwargs):
        return self.get(role).has(user, **kwargs)
    
roles = RoleManager()
        
class Permission(object):
    def __init__(self, name, description, roles, record=None, loaded=False):
        self.name = name
        self.roles = roles
        self.description = description
        self.loaded = loaded
        self.record = record
        
    def get_record(self):
        self.load()
        return self.record
    
    def get_roles_name(self, check=True):
        self.load(check)
    
        r = []
        for x in self.roles:
            if isinstance(x, (unicode, str)):
                r.append(x)
            else:
                #here x should be instance of Modal
                r.append(x.name)
        return r

    def get_roles(self, check=True):
        self.load(check)
    
        for i, x in enumerate(self.roles):
            self.roles[i] = roles.get(x)
        self.roles = filter(None, self.roles)
        return self.roles
    
    def add_role(self, role):
        role = roles.get(role).get_record()
            
        p = self.get_record()
        if not p.roles.has(role):
            p.roles.add(role)
            self.roles.append(role)
            
    def remove_role(self, role):
        role = roles.get(role).get_record()
            
        p = self.get_record()
        if p.roles.has(role):
            p.roles.delete(role)
            for i, x in enumerate(self.roles):
                if isinstance(x, (unicode, str)):
                    name = x
                else:
                    name = x.name
                if name == role.name:
                    del self.roles[i]
                    break

    def save(self):
        PermissionModel = get_model('permission')
        r = PermissionModel.get(PermissionModel.c.name==self.name)
        if not r:
            r = PermissionModel(name=self.name, description=self.description)
            r.save()
            
        r.roles.clear()
        for u in self.get_roles(False):
            r.roles.add(u.get_record())
            
        self.record = r
        
    def load(self, check=True):
        if not check:
            return
        if not self.loaded:
            PermissionModel = get_model('permission')
            r = PermissionModel.get(PermissionModel.c.name==self.name)
            if r:
                self.record = r
                self.description = r.description
                self.roles = list(r.roles.all())
#                if roles:
#                    self.roles = roles
                self.loaded = True
        
    def has(self, user, **kwargs):
        """
        user should be User's instance.
        """
        self.load()
        
        if isinstance(user, (unicode, str)):
            User = get_model('user')
            user = User.get(User.c.username==user)
            
        if not user:
            return False
        
        for r in self.get_roles():
            if r.has(user, **kwargs):
                return True
            
        return False
        
    def __repr__(self):
        return "<%s 'name':%r>" % (self.__class__.__name__, self.name)
    
class PermissionManager(object):
    def __init__(self):
        self.permissions = {}
        self.loaded = False
        
    def add(self, name, description, roles=[], record=None, loaded=False):
        p = self.permissions[name] = Permission(name, description, roles, record, loaded)
        return p
    
    def get(self, name):
        if name in self.permissions:
            return self.permissions[name]
        else:
            PermissionModel = get_model('permission')
            p = PermissionModel.get(PermissionModel.c.name==name)
            if p:
                return self.add(p.name, p.description, roles=list(p.roles.all()), record=p, loaded=True)
            else:
                raise PermissionError, "Permission [%s] is not existed!" % name
            
    
    def ok(self, name, user, **kwargs):
        return self.get(name).has(user, **kwargs)
    
permissions = PermissionManager()
