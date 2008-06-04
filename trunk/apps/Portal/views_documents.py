from frameworks.SimpleFrame import expose
from modules.menu import menu

def __begin__():
    response.menu=menu(request, 'Documents')

@expose('/documents')
def documents():
    return {}

from frameworks.SimpleFrame import static_serve
@expose('/documents/<regex(".*$"):filename>')
def show_document(filename):
    if not filename.endswith('.rst'):
        filename += '.rst'
    return locals()