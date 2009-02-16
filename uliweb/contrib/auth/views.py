from uliweb.core.SimpleFrame import expose

def login():
    from uliweb.contrib.auth import authenticate, login
    from forms import LoginForm
    
    form = LoginForm()
    
    if request.method == 'GET':
        form.next.data = request.GET.get('next', '/')
        return {'form':form, 'message':''}
    if request.method == 'POST':
        flag = form.check(request.params)
        if flag:
            f, d = authenticate(request, username=form.username.data, password=form.password.data)
            if f:
                login(request, form.username.data)
                next = request.POST.get('next', '/')
                return redirect(next)
            else:
                data = d
        message = "Login failed!"
        return {'form':form, 'message':message, 'message_type':'error'}

def register():
    from uliweb.contrib.auth import create_user
    from forms import RegisterForm
    
    form = RegisterForm()
    
    if request.method == 'GET':
        form.next.data = request.GET.get('next', '/')
        return {'form':form, 'message':''}
    if request.method == 'POST':
        flag = form.check(request.params)
        if flag:
            f, d = create_user(request, username=form.username.data, password=form.password.data)
            if f:
                next = request.POST.get('next', '/')
                return redirect(next)
            else:
                form.errors.update(d)
                
        message = "There was something wrong! Please fix them."
        return {'form':form, 'message':message, 'message_type':'error'}
        
def logout():
    from uliweb.contrib.auth import logout as out
    out(request)
    next = request.GET.get('next', '/')
    return redirect(next)
    
def admin():
    from forms import ChangePasswordForm
    changepasswordform = ChangePasswordForm()
    if request.method == 'GET':
        return {'changepasswordform':changepasswordform}
    if request.method == 'POST':
        if request.POST.get('action') == 'changepassword':
            flag = changepasswordform.check(request.POST, request)
            if flag:
                return redirect(request.path)
            else:
                message = "There was something wrong! Please fix them."
                return {'changepasswordform':changepasswordform, 
                    'message':message}
