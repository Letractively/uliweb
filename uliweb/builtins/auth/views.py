from uliweb.core.SimpleFrame import expose

@expose('/login')
def login():
    from uliweb.builtins.auth import authenticate, login
    from forms import LoginForm
    
    form = LoginForm()
    
    if request.method == 'GET':
        return {'form':form.html(), 'message':''}
    if request.method == 'POST':
        flag, data = form.validate(request.params)
        if flag:
            user = authenticate(request, username=data['username'], password=data['password'])
            if user:
                login(request, user)
                return redirect('/')
#            else:
#                return 'Login failed!'
#        else:
        message = "Login failed!"
        return {'form':form.html(request.params, data, py=False), 'message':message}

@expose('/register')
def register():
    from uliweb.builtins.auth import create_user, logined
    from forms import RegisterForm
    
    form = RegisterForm()
    
    if request.method == 'GET':
        return {'form':form.html(), 'message':''}
    if request.method == 'POST':
        flag, data = form.validate(request.params)
        if flag:
            user = create_user(request, username=data['username'], password=data['password'])
            if user:
                logined(request, user)
                return redirect('/')
            else:
                return 'Create user error!'
        else:
            message = "There was something wrong! Please fix them."
            return {'form':form.html(request.params, data, py=False), 'message':message}
        
@expose('/logout')
def logout():
    from uliweb.builtins.auth import logout
    logout(request)
    return redirect('/')
    