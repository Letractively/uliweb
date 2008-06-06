from frameworks.SimpleFrame import expose
from modules.menu import menu

def __begin__():
    response.menu=menu(request, 'Portal')
    
@expose('/')
def index():
    return {}

from frameworks.SimpleFrame import static_serve
@expose('/static/<regex(".*$"):filename>')
def static(filename):
    return static_serve(request, filename)
