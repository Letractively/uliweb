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
            f, d = authenticate(request, username=data['username'], password=data['password'])
            if f:
                login(request, d)
                return redirect('/')
            else:
                data = d
        message = "Login failed!"
        return {'form':form.html(request.params, data, py=False), 'message':message, 'message_type':'error'}

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
            f, d = create_user(request, username=data['username'], password=data['password'])
            if f:
                logined(request, d)
                return redirect('/')
            else:
                data = d
                
        message = "There was something wrong! Please fix them."
        return {'form':form.html(request.params, data, py=False), 'message':message}
        
@expose('/logout')
def logout():
    from uliweb.builtins.auth import logout
    logout(request)
    return redirect('/')
    