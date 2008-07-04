class TransactionMiddle(object):
    def __init__(self, application, config):
        from uliweb.orm import get_connection
        self.db = get_connection()
        
    def process_request(self, request):
        self.db.begin()

    def process_response(self, request, response):
        self.db.commit()
        return response
            
    def process_exception(self, request, exception):
        print 'xxxxxxxxxxxxxxxxxxxxxx'
        self.db.rollback()
    