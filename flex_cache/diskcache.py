from json import dumps, loads
from time import time
from diskcache import Cache as DCache
from .memcache import MemCache, MemCacheDecorator


class DiskCache(MemCache):
    """
    DiskCache inherits from MemCache since the underlying cache object is also dict-like.
    DiskCache must be initiated with a diskcache.Cache object to back the disk-based caching
    """
    def __init__(self, dcache=None, prefix="rc", serializer=dumps, deserializer=loads):
        dcache = dcache or DCache()
        # Use BaseCache init rather than the MemCache one..
        super(MemCache, self).__init__(DiskCacheDecorator, dcache, prefix, serializer, deserializer)


class DiskCacheDecorator(MemCacheDecorator):
    def __init__(self, cache, prefix='rc', serializer=dumps, deserializer=loads, ttl=0, limit=0, namespace=None):
        if limit != 0:
            raise ValueError('DiskCache does not support limits - only ttl')
        if ttl == 0:
            ttl = None
        super().__init__(cache, prefix, serializer, deserializer, ttl, limit, namespace)
