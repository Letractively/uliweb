from frameworks.SimpleFrame import expose
from utils import Form

@expose('/guest')
def guest(req):
    class F(Form.Form):
        content = Form.TextAreaField(label='Content:')
    
    f = F()
    if req.method == 'GET':
        return dict(form=f.html())
    elif req.method == 'POST':
        flag, data = f.validate(req.params)
        if flag:
            return dict(message='success', form='')
        else:
            return dict(form=f.html(req.params, data, py=False), message='')
