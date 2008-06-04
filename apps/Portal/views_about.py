from frameworks.SimpleFrame import expose
from modules.menu import menu

def __begin__():
    response.menu=menu(request, 'About')
    
@expose('/about')
def about():
    return {}
