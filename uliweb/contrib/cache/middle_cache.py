from uliweb.middleware import Middleware
from beaker.cache import CacheManager, Cache

class UliwebCache(Cache):
    def get(self, key, value=None, **kwargs):
        kw= kwargs.copy()
        if 'createfunc' not in kw:
            f = lambda x=value:value
            kw['createfunc'] = f
        return self._get_value(key, **kw).get_value()
    get_value = get

class UliwebCacheManager(CacheManager):
    def get_cache(self, name, **kwargs):
        kw = self.kwargs.copy()
        kw.update(kwargs)
        return self.caches.setdefault(name + str(kw), UliwebCache(name, **kw))
    
class CacheMiddle(Middleware):
    def __init__(self, application, settings):
        from beaker.util import coerce_cache_params

        options = settings.CACHE
        coerce_cache_params(options)
        self.cm = UliwebCacheManager(**options)
        self.cache = self.cm.get_cache('uliweb')
        application.cache = self.cache
        
    def process_request(self, request):
        request.cache = self.cache

