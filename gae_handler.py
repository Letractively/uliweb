import wsgiref.handlers
from manage import make_application
application = make_application()
wsgiref.handlers.CGIHandler().run(application)
