from uliweb.core.SimpleFrame import expose
from apps.Portal.modules.menu import menu
import os

def __begin__():
    response.menu=menu(request, 'Documents')

@expose('/documents')
def documents():
    return _show(request, 'content.rst', env)

def _show(request, filename, env, lang=None, render=True):
    from uliweb.core.template import template
    from uliweb.utils.rst import to_html
    from uliweb.i18n import get_language
    if not filename.endswith('.rst'):
        filename += '.rst'
    if not lang:
        #get from query string
        lang = request.GET.get('lang')
        if not lang:
            lang = get_language()
    if lang:
        f = env.get_file(os.path.join(lang, filename))
        if f:
            filename = f
    content = file(env.get_file(filename)).read()
    if render:
        content = to_html(template(content, env=env))
    else:
        content = to_html(content)
    return locals()
    
@expose('/documents/<regex(".*$"):filename>', defaults={'lang':''})
#@expose('/documents/<regex(".*$"):filename>')
#def show_document(filename, lang=''):
#this is also available
@expose('/documents/<lang>/<regex(".*$"):filename>')
def show_document(filename, lang):
    return _show(request, filename, env, lang, False)