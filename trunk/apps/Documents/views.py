from frameworks.SimpleFrame import expose
from modules.menu import menu
import os

def __begin__():
    response.menu=menu(request, 'Documents')

@expose('/documents')
def documents():
    return _show('toc.rst', env)

def _show(filename, env):
    from utils.template import template
    from utils.rst import to_html
    content = file(env.get_file(filename)).read()
    content = to_html(template(content, env), level=1)
    return locals()
    
@expose('/documents/<regex(".*$"):filename>')
def show_document(filename):
    if not filename.endswith('.rst'):
        filename += '.rst'
    return _show(filename, env)