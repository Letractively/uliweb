from uliweb.middleware import Middleware
from beaker.session import SessionObject

class Session(SessionObject):
    def __setattr__(self, value):
        super(Session, self).__setattr__(value)
        self.save()
        
class SessionMiddle(Middleware):
    def __init__(self, application, settings):
        from beaker.util import coerce_session_params
        from datetime import timedelta
        default = {
            'type':'dbm', 
            'data_dir':'./tmp/session', 
            'timeout':3600, 
            'encrypt_key':'uliweb', 
            'key':'uliweb.session.id',
            'table_name':'uliweb_table',
            'cookie_expires': 300
            
        }
        self.options = settings.get('SESSION', default)
        default.update(self.options)
        self.options = default
        if isinstance(default['cookie_expires'], int):
            default['cookie_expires'] = timedelta(seconds=default['cookie_expires'])
        coerce_session_params(self.options)
        
    def process_request(self, request):
        session = SessionObject(request.environ, **self.options)
        request.session = session

    def process_response(self, request, response):
        session = request.session
        session.save()
        session.persist()
        if session.request is not None:
            if session.request['set_cookie']:
                cookie = session.request['cookie_out']
                if cookie:
                    response.headers['Set-cookie'] = cookie
        return response
        
