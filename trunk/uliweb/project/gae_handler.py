import wsgiref.handlers
from manage import make_application
application = make_application(False)
wsgiref.handlers.CGIHandler().run(application)
