from frameworks.SimpleFrame import expose

def __begin__():
    response.menu=[
      [True, 'Home', '/'],
      [False, 'Examples', '/examples'],
      [False, 'About', '/about'],
    ]
    
@expose('/')
def index():
    return {}

from frameworks.SimpleFrame import static_serve
@expose('/static/<regex(".*$"):filename>')
def static(filename):
    return static_serve(request, filename)
