#coding=utf-8
from uliweb.core.SimpleFrame import expose

@expose('/post')
def post():
    from forms import ContentForm
    from uliweb.i18n.html_helper import make_select_languages
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
    
    change_languages = make_select_languages(config.get('LANGUAGES', []), request.path_info)
    return locals()

