import wsgiref.handlers
from manage import make_app
wsgiref.handlers.CGIHandler().run(make_app())
