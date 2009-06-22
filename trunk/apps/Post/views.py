#coding=utf-8
from uliweb.core.SimpleFrame import expose

@expose('/post')
def post():
    from forms import ContentForm
    from uliweb.i18n.html_helper import make_select_languages
    form = ContentForm()
    content = ''
    if request.method == 'POST':
        flag = form.validate(request.params)
        if flag:
            from uliweb.utils.rst import to_html
            content = to_html(form.content.data)
    change_languages = make_select_languages(['en', 'zh_CN'])
    return {'content':content, 'form':form, 'change_languages':change_languages}

