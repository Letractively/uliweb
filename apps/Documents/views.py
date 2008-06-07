from frameworks.SimpleFrame import expose
from modules.menu import menu
import os

def __begin__():
    response.menu=menu(request, 'Documents')

@expose('/documents')
def documents():
    return _show('toc.rst', env)

def _show(filename, env, render=True):
    from utils.template import template
    from utils.rst import to_html
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
    if not filename.endswith('.rst'):
        filename += '.rst'
    if lang:
        filename = os.path.join(lang, filename)
    return _show(filename, env, False)