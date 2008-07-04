from models import User

def get_user(user_id):
    return User.get(user_id)

def authenticate(username, password):
    user = User.get(User.c.username==username)
    if user:
        if user.check_password(password):
            return user
    
def create_user(**kwargs):
    password = kwargs.pop('password', '')
    user = User(**kwargs)
    user.set_password(password)
    user.save()
    return user
    