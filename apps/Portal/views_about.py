from frameworks.SimpleFrame import expose

def __begin__():
    response.menu=[
      [False, 'Home', '/'],
      [False, 'Examples', '/examples'],
      [True, 'About', '/about'],
    ]
    
@expose('/about')
def about():
    return {}
