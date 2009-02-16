from models import User
from uliweb.core.plugin import plugin, LOW
from uliweb.utils.common import log

@plugin('get_user', signal=(None, 'default'), kind=LOW)
def get_user(request, user_id):
    return User.get(user_id)

@plugin('authenticate', signal=(None, 'default'), kind=LOW)
def authenticate(request, username, password):
    user = User.get(User.c.username==username)
    if user:
        if user.check_password(password):
            return True, 'default'
        else:
            return False, {'password': "Password isn't correct!"}
    else:
        return False, {'username': 'Username is not existed!'}
    
@plugin('create_user', signal=(None, 'default'), kind=LOW)
def create_user(request, username, password, **kwargs):
    try:
        user = User.get(User.c.username==username)
        if user:
            return False, {'username':"Username is already existed!"}
        user = User(username=username, password=password)
        user.set_password(password)
        user.save()
        return True, user
    except Exception, e:
        log.exception(e)
        return False, {'_': "Creating user failed!"}
    
@plugin('delete_user', signal=(None, 'default'), kind=LOW)
def delete_user(request, username):
    return True

@plugin('change_password', signal=(None, 'default'), kind=LOW)
def change_password(request, username, password):
    user = User.get(User.c.username==username)
    user.set_password(password)
    user.save()
    return True

@plugin('login', signal=(None, 'default'), kind=LOW)
def login(request, username):
    return True

@plugin('logout', signal=(None, 'default'), kind=LOW)
def logout(request, username):
    return True
