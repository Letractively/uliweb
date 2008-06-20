import sys, os
path = os.path.dirname(__file__)
sys.path.insert(0, path)
from manage import make_application
application = make_application()
import logging
logging.error(application.config.DEBUG)
if application.config.DEBUG:
    from werkzeug.debug import DebuggedApplication
    application = DebuggedApplication(application)
    