from uliweb.core.SimpleFrame import expose
from Portal.modules.menu import menu
from uliweb.utils.cache import get_cache

cache = get_cache()

def __begin__():
    response.menu=menu(request, 'Portal')
    
@cache.page()
@expose('/')
def index():
    return {}

from uliweb.utils.filedown import filedown

@expose('/favicon.ico', static=True)
def favicon():
    return filedown(request.environ, application.get_file('favicon.ico'))

@expose('/robots.txt', static=True)
def robots():
    return filedown(request.environ, application.get_file('robots.txt'))
