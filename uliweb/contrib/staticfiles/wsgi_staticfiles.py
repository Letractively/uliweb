import os
from werkzeug import ClosingIterator

class StaticFilesMiddleware(object):
    """
    This WSGI middleware is changed from werkzeug ShareDataMiddleware, but
    I made it Uliweb compatable.
    """

    def __init__(self, app, STATIC_URL, disallow=None):
        self.app = app
        self.url_suffix = STATIC_URL.rstrip('/') + '/'
        if disallow is not None:
            from fnmatch import fnmatch
            self.is_allowed = lambda x: not fnmatch(x, disallow)

    def is_allowed(self, filename):
        """Subclasses can override this method to disallow the access to
        certain files.  However by providing `disallow` in the constructor
        this method is overwritten.
        """
        return True

    def __call__(self, environ, start_response):
        # sanitize the path for non unix systems
        path = environ.get('PATH_INFO', '')
        if path.startswith(self.url_suffix):
            filename = path[len(self.url_suffix):]
        else:
            return self.app(environ, start_response)
        if not self.is_allowed(filename):
            from werkzeug.exceptions import Forbidden
            return Forbidden('The file %s is forbidden' % filename)
        
        from uliweb.core.SimpleFrame import static_serve
        response = static_serve(self.mainapplication, filename, dir=self.mainapplication.settings.STATICFILES.STATIC_FOLDER)
        return response(environ, start_response)
