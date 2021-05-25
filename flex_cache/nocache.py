from json import dumps, loads
from functools import wraps
from .basecache import BaseCache, BaseCacheDecorator


class NoCache(BaseCache):
    def __init__(self, prefix="rc", serializer=dumps, deserializer=loads):
        super().__init__(NoCacheDecorator, dict(), prefix, serializer, deserializer)

    def mget(self, *fns_with_args):
        raise NotImplementedError('This is not a real cache..')


class NoCacheDecorator(BaseCacheDecorator):

    def __call__(self, fn):

        @wraps(fn)
        def inner(*args, **kwargs):
            return fn(*args, **kwargs)

        inner.invalidate = self.invalidate
        inner.invalidate_all = self.invalidate_all
        inner.instance = self
        return inner

    def check_cache(self, key):
        return None

    def cache_output(self, key, serialized):
        pass

    def invalidate_key(self, key):
        pass

