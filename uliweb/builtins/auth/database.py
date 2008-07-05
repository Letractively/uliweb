from models import User

def get_user(user_id):
    return User.get(user_id)

def authenticate(username, password):
    user = User.get(User.c.username==username)
    if user:
        if user.check_password(password):
            return True, user
        else:
            return False, {'password': "Password isn't correct!"}
    else:
        return False, {'username': 'Username is not existed!'}
    
def create_user(username, password):
    try:
        user = User.get(User.c.username==username)
        if user:
            return False, {'username':"Username is already existed!"}
        user = User(username=username, password=password)
        user.set_password(password)
        user.save()
        return True, user
    except:
        return False, {'_': "Creating user failed!"}