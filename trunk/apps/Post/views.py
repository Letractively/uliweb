#coding=utf-8
from uliweb.core.SimpleFrame import expose

def __begin__():
    from uliweb.core.i18n import set_language
    set_language('zh')

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

@expose('/post1')
def post1():
    from uliweb.core.i18n import set_language
    set_language('en')
    response.view = 'post.html'
    return post()
