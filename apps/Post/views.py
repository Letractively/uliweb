#coding=utf-8
from frameworks.SimpleFrame import expose

@expose('/post')
def post():
    from forms import ContentForm
    
    form = ContentForm()
    content = ''
    if request.method == 'POST':
        flag, data = form.validate(request.params)
        if flag:
            from utils.rst import to_html
            content = to_html(data.content)
            form = form.html(data)
        else:
            form = form.html(request.params, data, py=False)
        
    return locals()