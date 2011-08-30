from uliweb.middleware import Middleware
import threading
from uliweb.orm import Begin, Commit, Rollback

class TransactionMiddle(Middleware):
    ORDER = 100
    
    def __init__(self, application, settings):
        pass
        
    def process_request(self, request):
        Begin(create=True)

    def process_response(self, request, response):
        try:
            return response
        finally:
            Commit(close=True)
            
    def process_exception(self, request, exception):
        Rollback(close=True)
        