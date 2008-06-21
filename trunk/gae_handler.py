import wsgiref.handlers
from manage import make_application

application = make_application()
if application.config.DEBUG:
    from werkzeug.debug import DebuggedApplication
    application = DebuggedApplication(application)

wsgiref.handlers.CGIHandler().run(application)
