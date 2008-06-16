from uliweb.core.SimpleFrame import expose
from apps.Portal.modules.menu import menu

def __begin__():
    response.menu=menu(request, 'About')
    
@expose('/about')
def about():
    return {}
