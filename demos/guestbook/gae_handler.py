import os, sys
import wsgiref.handlers
from uliweb.manage import make_application

sys.path.insert(0, os.path.dirname(__file__))

application = make_application(False, os.path.join(os.path.dirname(__file__), 'apps'))
wsgiref.handlers.CGIHandler().run(application)
