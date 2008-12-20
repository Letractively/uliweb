from uliweb.middlewares import Middleware

class CacheMiddle(Middleware):
    def __init__(self, application, settings):
        from beaker.cache import CacheManager
        from beaker.util import coerce_cache_params

        options = settings.CACHE
        coerce_cache_params(options)
        self.cm = CacheManager(**options)
        self.cache = self.cm.get_cache('uliweb')
        application.cache = self.cache
        
    def process_request(self, request):
        request.cache = self.cache

