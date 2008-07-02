class CacheMiddle(object):
    def __init__(self, application, config):
        from beaker.cache import CacheManager
        from beaker.util import coerce_cache_params
        default = {
            'type':'dbm', 
            'data_dir':'./tmp/cache', 
            'expiretime':3600,
            'table_name':'uliweb_cache'
        }

        options = config.get('CACHE_CONFIG', default)
        default.update(options)
        options = default
        coerce_cache_params(options)
        self.cm = CacheManager(**options)
        self.cache = self.cm.get_cache('uliweb')
        application.cache = self.cache
        
    def process_request(self, request):
        request.cache = self.cache

