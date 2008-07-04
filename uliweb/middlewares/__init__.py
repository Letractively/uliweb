class Middleware(object):
    def __init__(self, application, config):
        self.application = application
        self.config = config
        
#    def process_request(self, request):
#        pass
#    
#    def process_response(self, request, response):
#        pass
#    
#    def process_exception(self, request, exception):
#        pass