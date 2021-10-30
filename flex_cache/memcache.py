from json import dumps, loads
from time import time
from threading import Lock
from .basecache import BaseCache, BaseCacheDecorator


class CachedItem(object):
    def __init__(self, key, value, duration=60):
        self.key = key
        self.value = value
        self.duration = duration
        self.timestamp = time()

    def expired(self):
        if self.duration == 0:
            return False
        return self.timestamp + self.duration < time()

    def __repr__(self):
        return '<CachedItem {%s:%s} expires at: %s>' % (self.key, self.value, self.timestamp + self.duration)


class CachedDict(dict):
    def __init__(self, seq=None, **kwargs):
        super().__init__(seq=seq, **kwargs)
        self.lock = Lock()
        self.prune_count = 0
        self.prune_threshold = kwargs.get('prune_threshold', 50)

    def _prune(self):
        """
        Prune with lock + copy & replace:
        executed 80000 threaded inserts in 8.680633068084717 seconds
        Prune with copy before lock & replace:
        executed 80000 threaded inserts in 8.535555124282837 seconds
        Prune with lock + compile expired & delete (selected):
        executed 80000 threaded inserts in 7.83364725112915 seconds
        Returns:

        """
        self.prune_count += 1
        if self.prune_count < self.prune_threshold:
            return
        self.prune_count = 0
        with self.lock:
            obsolete = [k for k, v in self.items() if isinstance(v, CachedItem) and v.expired()]
            for k in obsolete:
                del self[k]

    def get(self, key):
        val = self.get(key)
        if not val:
            return None
        elif val.expired():
            with self.lock:
                del self[key]
            return None
        else:
            return val.value

    def set(self, key, value, duration=60):
        with self.lock:
            self[key] = CachedItem(key, value, duration)
        self._prune()


class MemCache(BaseCache):
    def __init__(self, prefix="rc", serializer=dumps, deserializer=loads):
        super().__init__(MemCacheDecorator, CachedDict(), prefix, serializer, deserializer)

    def mget(self, *fns_with_args):
        keys = self.mget_keys(*fns_with_args)
        results = {key: self._cache.get(key) for key in keys}
        return [self.deserializer(v) for k,v in results.items() if v]


class MemCacheDecorator(BaseCacheDecorator):
    def __init__(self, cache, prefix='rc', serializer=dumps, deserializer=loads, ttl=0, limit=0, namespace=None):
        if limit != 0:
            raise ValueError('MemCache does not support limits - only ttl')
        super().__init__(cache, prefix, serializer, deserializer, ttl, limit, namespace)

    def check_cache(self, key):
        return self.cache.get(key)

    def cache_output(self, key, serialized):
        self.cache.set(key, serialized, self.ttl)

    def invalidate_key(self, key):
        try:
            del self.cache[key]
        except KeyError:
            pass  # already invalidated..

    def invalidate_all(self, *args, **kwargs):
        if not self.namespace or not self.cache:
            return
        invalidated = [k for k in self.cache if self.namespace in k]
        for k in invalidated:
            del self.cache[k]
