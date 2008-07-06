__backends = {}

def _import_backend(type):
    if not type:
        type = 'database'
    if type in __backends:
        return __backends[type]
    
    if type == 'database':
        import database as mod
        
    __backends[type] = mod
    return mod

def _get_auth_key(request):
    return request.settings.get('AUTH_KEY', '__uliweb_session_user_id__')

def _get_backend_key(request):
    return request.settings.get('BACKEND_KEY', '__uliweb_session_backend_id__')

def get_user(request):
    session_key = _get_auth_key(request)
    user_id = request.session.get(session_key)
    backend_key = _get_backend_key(request)
    backend_id = request.session.get(backend_key)
    if user_id:
        return _get_user(request, user_id, backend_id)

def _get_user(request, user_id, backend_id=None):
    mod = _import_backend(backend_id)
    user = mod.get_user(user_id)
    if user:
        return user
     
def create_user(request, backend_id=None, **kwargs):
    mod = _import_backend(backend_id)
    flag, user = mod.create_user(**kwargs)
    return flag, user
    
def authenticate(request, username, password, backend_id=None):
    """
    If the given credentials are valid, return a User object.
    """
    mod = _import_backend(backend_id)
    flag, user = mod.authenticate(username, password)
    if flag:
        login(request, user, backend_id)
    return flag, user

def logined(request, user, backend_id=None):
    request.session[_get_auth_key(request)] = user.id
    backend_id = backend_id or 'database'
    request.session[_get_backend_key(request)] = backend_id
    
def login(request, user, backend_id=None):
    """
    Persist a user id and a backend in the request. This way a user doesn't
    have to reauthenticate on every request.
    """
    backend_id = backend_id or 'database'
    
    import datetime
    
    if user is None:
        user = request.user
    # TODO: It would be nice to support different login methods, like signed cookies.
    user.last_login = datetime.datetime.now()
    user.save()
    request.session[_get_auth_key(request)] = user.id
    request.session[_get_backend_key(request)] = backend_id
    if hasattr(request, 'user'):
        request.user = user

def logout(request):
    """
    Remove the authenticated user's ID from the request.
    """
    try:
        del request.session[_get_auth_key(request)]
    except KeyError:
        pass
    try:
        del request.session[_get_backend_key(request)]
    except KeyError:
        pass
    if hasattr(request, 'user'):
        request.user = None
    