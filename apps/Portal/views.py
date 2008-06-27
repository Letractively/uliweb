from uliweb.core.SimpleFrame import expose
from apps.Portal.modules.menu import menu

def __begin__():
    response.menu=menu(request, 'Portal')
    
@expose('/')
def index():
    return {}

from uliweb.core.SimpleFrame import static_serve
@expose('/static/<path:filename>')
def static(filename):
    return static_serve(request, filename)

@expose('/favicon.ico')
def favicon():
    return static_serve(request, 'favicon.ico')

@expose('/robots.txt')
def robots():
    return static_serve(request, 'robots.txt')
