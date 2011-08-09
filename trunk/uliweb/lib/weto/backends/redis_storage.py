from base import BaseStorage
import cPickle
import redis

#connection pool format should be: (options, connection object)
__connection_pool__ = None

class Storage(BaseStorage):
    def __init__(self, options):
        """
        options =
            unix_socket_path = '/tmp/redis.sock'
            or
            connection_pool = {'host':'localhost', 'port':6379, 'db':0}
        """
        BaseStorage.__init__(self, options)

        if 'unix_socket_path' in options:
            self.redis = redis.Redis(unix_socket_path=options['unix_socket_path'])
        else:
            global __connection_pool__
        
            if not __connection_pool__ or __connection_pool__[0] != options['connection_pool']:
                d = {'host':'localhost', 'port':6379}
                d.update(options['connection_pool'])
                __connection_pool__ = (d, redis.ConnectionPool(**d))
            self.redis = redis.Redis(connection_pool=__connection_pool__[1])
            
    def load(self, key):
        v = self.redis.get(key)
        if v is not None:
            return cPickle.loads(v)
    
    def save(self, key, stored_time, expiry_time, value, modified):
        v =cPickle.dumps(value, cPickle.HIGHEST_PROTOCOL)
        pipe = self.redis.pipeline()
        return pipe.set(key, v).expire(key, expiry_time).execute()
    
    def delete(self, key):
        self.redis.delete(key)
        
    def read_ready(self, key):
        return True
    
    def get_lock(self, key):
        pass
    
    def acquire_read_lock(self, lock):
        pass
        
    def release_read_lock(self, lock, success):
        pass
        
    def acquire_write_lock(self, lock):
        pass
        
    def release_write_lock(self, lock, success):
        pass
    
    def delete_lock(self, lock):
        pass
    
    