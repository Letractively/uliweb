from uliweb.core.SimpleFrame import expose

@expose('/login')
def login():
    from uliweb.contrib.auth import authenticate, login
    from forms import LoginForm
    from uliweb.form import CSSLayout
    
    form = LoginForm(title='Login')
    form.layout_class = CSSLayout
    
    if request.method == 'GET':
        form.next.data = request.GET.get('next', '/')
        return {'form':form, 'message':''}
    if request.method == 'POST':
        flag = form.check(request.params)
        if flag:
            f, d = authenticate(request, username=form.username.data, password=form.password.data)
            if f:
                login(request, d)
                next = request.POST.get('next', '/')
                return redirect(next)
            else:
                data = d
        message = "Login failed!"
        return {'form':form, 'message':message, 'message_type':'error'}

@expose('/register')
def register():
    from uliweb.contrib.auth import create_user, logined
    from forms import RegisterForm
    from uliweb.form import CSSLayout
    
    form = RegisterForm(title='Register')
    form.layout_class = CSSLayout
    
    if request.method == 'GET':
        form.next.data = request.GET.get('next', '/')
        return {'form':form, 'message':''}
    if request.method == 'POST':
        flag = form.check(request.params)
        if flag:
            f, d = create_user(request, username=form.username.data, password=form.password.data)
            if f:
                logined(request, d)
                next = request.POST.get('next', '/')
                return redirect(next)
            else:
                form.errors.update(d)
                
        message = "There was something wrong! Please fix them."
        return {'form':form, 'message':message, 'message_type':'error'}
        
@expose('/logout')
def logout():
    from uliweb.contrib.auth import logout as out
    out(request)
    next = request.GET.get('next', '/')
    return redirect(next)
    