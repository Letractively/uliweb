from uliweb.utils.common import log
from uliweb.core.plugin import callplugin, execplugin
import database
from models import User

class CreatingUserError(Exception):pass

def _get_auth_key(request):
    return request.settings.AUTH.AUTH_KEY

def _get_backend_key(request):
    return request.settings.AUTH.BACKEND_KEY

def get_user(request):
    """
    return user, backend_id
    """
    session_key = _get_auth_key(request)
    user_id = request.session.get(session_key)
    backend_key = _get_backend_key(request)
    backend_id = request.session.get(backend_key)
    if user_id:
        return execplugin(request, 'get_user', user_id, signal=backend_id)

def create_user(request, username, password, backend_id=None, **kwargs):
    """
    return flag, result(result can be an User object or just True, {} for errors)
    """
    
    v = execplugin(request, 'create_user', username, password, signal=backend_id, **kwargs)
    flag, result = v
    if flag:
        if not isinstance(result, User):
            user = User.get(User.c.username==username)
            if not user:
                user = User(username=username, **kwargs)
                user.save()
        else:
            user = result
        return True, user
    return flag, result
    
def change_password(request, username, password, backend_id=None):
    return execplugin(request, 'change_password', username, password, signal=backend_id)

def delete_user(request, username, backend_id=None):
    result = execplugin(request, 'delete_user', username, signal=backend_id)
    if result:
        user = User.get(User.c.username==username)
        if user:
            user.delete()
    return result
    
def authenticate(request, username, password, backend_id=None):
    """
    return flag, result, if flag == True, result will be backend_id
    if flag == False, result will be the error message({}):
    """
    flag, backend = execplugin(request, 'authenticate', username, password, signal=backend_id)
    return flag, backend

def login(request, username, backend_id=None):
    """
    return user, backend_id
    """
    result = execplugin(request, 'login', username, signal=backend_id)
    if result:
        import datetime
        
        user = User.get(User.c.username==username)
        user.last_login = datetime.datetime.now()
        user.save()
        request.session[_get_auth_key(request)] = user.id
        request.session[_get_backend_key(request)] = backend_id
        if hasattr(request, 'user'):
            request.user = user
    return result
    
def logout(request, backend_id=None):
    """
    Remove the authenticated user's ID from the request.
    """
    result = execplugin(request, 'logout', request.user.username, signal=backend_id)
    if result:
        try:
            del request.session[_get_auth_key(request)]
        except KeyError:
            pass
        try:
            del request.session[_get_backend_key(request)]
        except KeyError:
            pass
        request.user = None
    return result