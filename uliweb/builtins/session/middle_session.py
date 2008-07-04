from uliweb.middlewares import Middleware

class SessionMiddle(Middleware):
    def __init__(self, application, config):
        from beaker.util import coerce_session_params
        from datetime import timedelta
        default = {
            'type':'dbm', 
            'data_dir':'./tmp/session', 
            'timeout':3600, 
            'encrypt_key':'uliweb', 
            'key':'uliweb.session.id',
            'table_name':'uliweb_table'
        }
        self.options = config.get('SESSION_CONFIG', default)
        default.update(self.options)
        self.options = default
        if isinstance(default['cookie_expires'], int):
            default['cookie_expires'] = timedelta(seconds=default['cookie_expires'])
        coerce_session_params(self.options)
        
    def process_request(self, request):
        from beaker.session import SessionObject
        session = SessionObject(request.environ, **self.options)
        request.session = session

    def process_response(self, request, response):
        session = request.session
        session.save()
        if session.__dict__['_sess'] is not None:
            if session.__dict__['_headers']['set_cookie']:
                cookie = session.__dict__['_headers']['cookie_out']
                if cookie:
                    response.headers['Set-cookie'] = cookie
        return response
        
