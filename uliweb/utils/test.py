from uliweb.core import SimpleFrame
from StringIO import StringIO
import sys
import mimetools
from wsgiref.headers import Headers

def make_headers():
    return mimetools.Message(StringIO(), 0)

def make_environ(url, method='GET', data='', headers=None, env=None):
    from urllib import unquote
    
    env = env or {}
    headers = headers or make_headers()
    
    if '?' in url:
        path_info, query = url.split('?', 1)
    else:
        path_info = url
        query = ''
    environ = {
        'wsgi.version':         (1, 0),
        'wsgi.url_scheme':      'http',
        'wsgi.input':           StringIO(data),
        'wsgi.errors':          sys.stderr,
        'wsgi.multithread':     True,
        'wsgi.multiprocess':    True,
        'wsgi.run_once':        False,
        'SERVER_SOFTWARE':      0.1,
        'REQUEST_METHOD':       method,
        'SCRIPT_NAME':          '',
        'PATH_INFO':            unquote(path_info),
        'QUERY_STRING':         query,
        'CONTENT_TYPE':         headers.get('Content-Type', ''),
        'CONTENT_LENGTH':       headers.get('Content-Length', ''),
        'REMOTE_ADDR':          'localhost',
        'REMOTE_PORT':          8000,
        'SERVER_NAME':          'uliweb.server',
        'SERVER_PORT':          '8000',
        'SERVER_PROTOCOL':      '1.0'
    }

    for key, value in headers.items():
        key = 'HTTP_' + key.upper().replace('-', '_')
        if key not in ('HTTP_CONTENT_TYPE', 'HTTP_CONTENT_LENGTH'):
            environ[key] = value

    environ.update(env)
        
    return environ

def BlankRequest(url, method='GET', data='', headers=None, env=None):
    from uliweb.core.SimpleFrame import Request
    return Request(make_environ(url=url, method=method, data=data, headers=headers, env=env))

class Client(object):
    def __init__(self, apps_dir='apps', settings='settings.ini'):
        if apps_dir not in sys.path:
            sys.path.insert(0, apps_dir)
        self.app = SimpleFrame.Dispatcher(apps_dir=apps_dir, start=False, settings_file=settings)
        self.stdout = sys.stdout
        
    def get(self, url, headers=None, env=None):
        environ = make_environ(url, method='GET', headers=headers, env=env)
        return ''.join(self.app(environ, self.start_response))
        
    def post(self, url, data=None, headers=None, env=None):
        environ = make_environ(url, method='POST', data=data, headers=headers, env=env)
        return ''.join(self.app(environ, self.start_response))
        
    def start_response(self, status, headers):
        self.status = status
        self.headers = Headers(headers)
        return self.write
    
    def write(self, data):
        self.bytes_sent = len(data)    # make sure we know content-length
        self.send_headers()
        self._write(data)
        self._flush()
    
    def _write(self,data):
        self.stdout.write(data)
    
    def _flush(self):
        self.stdout.flush()
    
    