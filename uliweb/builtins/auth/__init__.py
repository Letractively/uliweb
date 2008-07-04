__backends = {}

def _import_backend(type):
    if type in __backends:
        return __backends[type]
    
    if type == 'database':
        import database as mod
        
    __backends[type] = mod
    return mod

def _get_auth_key(request):
    return request.config.get('AUTH_KEY', '__uliweb_session_user_id__')

def _get_auth_backend(request):
    return request.config.get('AUTH_BACKENDS', ['database'])

def get_user(request):
    session_key = _get_auth_key(request)
    user_id = request.session.get(session_key)
    if user_id:
        return _get_user(request, user_id)

def _get_user(request, user_id):
    backends = _get_auth_backend(request)
    for b in backends:
        mod = _import_backend(b)
        user = mod.get_user(user_id)
        if user:
            return user
     
def create_user(request, **kwargs):
    backends = _get_auth_backend(request)
    for b in backends:
        mod = _import_backend(b)
        user = mod.create_user(**kwargs)
        if user:
            return user
    
def authenticate(request, username, password):
    """
    If the given credentials are valid, return a User object.
    """
    backends = _get_auth_backend(request)
    for b in backends:
        mod = _import_backend(b)
        user = mod.authenticate(username, password)
        if user:
            login(request, user)
            return user

def logined(request, user):
    request.session[_get_auth_key(request)] = user.id
    
def login(request, user):
    """
    Persist a user id and a backend in the request. This way a user doesn't
    have to reauthenticate on every request.
    """
    import datetime
    
    if user is None:
        user = request.user
    # TODO: It would be nice to support different login methods, like signed cookies.
    user.last_login = datetime.datetime.now()
    user.save()
    request.session[_get_auth_key(request)] = user.id
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
    if hasattr(request, 'user'):
        request.user = None
    