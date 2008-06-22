from uliweb.core.SimpleFrame import expose
from apps.Portal.modules.menu import menu
import os

def __begin__():
    response.menu=menu(request, 'Documents')

@expose('/documents')
def documents():
    return _show(request, response, 'content.rst', env)

def _show(request, response, filename, env, lang=None, render=True):
    from uliweb.core.template import template
    from uliweb.utils.rst import to_html
    from uliweb.i18n import get_language, format_locale
    if not filename.endswith('.rst'):
        filename += '.rst'
    if not lang:
        #get from query string, and auto set_cookie
        lang = request.GET.get('lang')
        if not lang:
            lang = get_language()
        else:
            response.set_cookie(env.config.get('LANGUAGE_COOKIE_NAME'), lang)
    if lang:
        lang = format_locale(lang)
        f = env.get_file(os.path.join(lang, filename))
        if f:
            filename = f
    content = file(env.get_file(filename)).read()
    if render:
        content = to_html(template(content, env=env))
    else:
        content = to_html(content)
    response.write(application.template('show_document.html', locals()))
    return response
    
@expose('/documents/<regex(".*$"):filename>', defaults={'lang':''})
#@expose('/documents/<regex(".*$"):filename>')
#def show_document(filename, lang=''):
#this is also available
@expose('/documents/<lang>/<regex(".*$"):filename>')
def show_document(filename, lang):
    return _show(request, response, filename, env, lang, False)