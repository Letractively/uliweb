from uliweb.core.SimpleFrame import expose
from apps.Portal.modules.menu import menu
import uliweb.form.uliform as Form

def __begin__():
    response.menu=menu(request, 'Examples')

@expose('/examples')
def examples_index():
    return {}

@expose
def examples_template():
    title="This is a template test"
    return locals()

@expose
def examples_redirect():
    return redirect(url_for('%s.views.examples_index' % request.appname))

@expose
def examples_response():
    response.write("<p>This test is directly use response object in view function</p>")
    return response

@expose
def examples_form():
    class F(Form.Form):
        title = Form.StringField(label='Title:', required=True, help_string='Title help string')
        content = Form.TextField(label='Content:')
        age = Form.IntField(label='Age:')
        id = Form.HiddenField()
        tag = Form.ListField(label='Tag:')
        public = Form.BooleanField(label='Public:')
        format = Form.SelectField(label='Format:', choices=[('rst', 'reStructureText'), ('text', 'Plain Text')], default='rst')
        radio = Form.RadioSelectField(label='Radio:', choices=[('rst', 'reStructureText'), ('text', 'Plain Text')], default='rst')
        file = Form.FileField(label='file')
    
    f = F()
    if request.method == 'GET':
        return dict(form=f, message='')
    elif request.method == 'POST':
        flag = f.check(request.params)
        if flag:
            return dict(message='success', form='')
        else:
            return dict(form=f, message='')
        
@expose
def examples_error():
    error(message='This is error test!')
    
@expose
def examples_print_settings():
    return '<pre>' + str(settings) + '</pre>'

@expose
def examples_cookie():
    c = request.cookies.get('name', 'no-cookie')
    response.set_cookie('name', 'limodou')
    response.write('cookie name=' + c)
    return response

@expose
def examples_cache():
    import time
    r = request.cache.get('name', time.asctime(), expiretime=10)
    return 'Current Time= %s<br>Cache Value=%s' % (time.asctime(), r)

@expose
def examples_session():
    import time
    name = request.session.get('username')
    if not name:
        s = "You have not registered, now you'll be registered automatically"
        request.session['username'] = 'limodou'
        request.session.save()
    else:
        s = "Welcome %s" % name
    return s

@expose
def examples_htmlhelper():
    return {}

@expose
def examples_jxlib():
    return {}
