import wsgiref.handlers
from manage import make_application
wsgiref.handlers.CGIHandler().run(make_application())
