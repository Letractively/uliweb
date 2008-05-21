from frameworks.SimpleFrame import expose

@expose('/')
def index():
    return {}

@expose('/template')
def template():
    title="This is a template test"
    return locals()

@expose('/redirect')
def test_redirect():
    redirect(url_for('%s.views.index' % request.appname))

@expose
def simple_expose():
    return '''@expose
def simple_expose(req):
    return 
'''

@expose
def simple_expose_para(name):
    return '''@expose
def simple_expose_para(req, name):
    return
'''

@expose
def test_response():
    response.write("<p>This test is directly use response object in view function</p>")
    return response

@expose('/form')
def form():
    class F(Form.Form):
        title = Form.TextField(label='Title:', required=True, help_string='Title help string')
        content = Form.TextAreaField(label='Content:')
        age = Form.IntField(label='Age:')
        id = Form.HiddenField()
        tag = Form.TextListField(label='Tag:')
        public = Form.BooleanField(label='Public:')
        format = Form.SelectField(label='Format:', choices=[('rst', 'reStructureText'), ('text', 'Plain Text')], default='rst')
        radio = Form.RadioSelectField(label='Radio:', choices=[('rst', 'reStructureText'), ('text', 'Plain Text')], default='rst')
        file = Form.FileField(label='file')
    
    f = F()
    if request.method == 'GET':
        return dict(form=f.html(), message='')
    elif request.method == 'POST':
        flag, data = f.validate(request.params)
        if flag:
            return dict(message='success', form='')
        else:
            return dict(form=f.html(request.params, data, py=False), message='')
        
from frameworks.SimpleFrame import static_serve
@expose('/static/<regex(".*$"):filename>')
def static(filename):
    return static_serve(request, filename)

@expose
def test_error():
    error(message='This is error test!')
    
@expose
def print_config():
    return '<br/>'.join(["%s = %r" % (k,v) for k, v in config.iteritems()])