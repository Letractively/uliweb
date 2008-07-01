class CacheMiddle(object):
    def __init__(self, application, config):
        from beaker.cache import CacheManager
        default = config.get('CACHE_CONFIG', {'type':'dbm', 'data_dir':'./cache'})
        self.cm = CacheManager(**default)
        self.cache = self.cm.get_cache('uliweb')
        application.cache = self.cache
        
    def process_request(self, request):
        request.cache = self.cache

