[![CI](https://github.com/steffenschumacher/python-flex-cache/actions/workflows/CI.yml/badge.svg?branch=master&event=push)](https://github.com/steffenschumacher/python-flex-cache/actions/workflows/CI.yml)
[![pypi](https://img.shields.io/pypi/v/python-flex-cache.svg)](https://pypi.python.org/pypi/python-flex-cache)
[![versions](https://img.shields.io/pypi/pyversions/python-flex-cache.svg)](https://github.com/steffenschumacher/python-flex-cache)
[![license](https://img.shields.io/github/license/steffenschumacher/python-flex-cache.svg)](https://github.com/steffenschumacher/python-flex-cache/blob/master/LICENSE)
# python-flex-cache
Simple & flexible caching for Python functions backed by either redis, disk or memory

### Requirements
- Redis 5+
- Python 3.6+

## How to install
```
pip install python-flex-cache
```

## How to use
### Initialize through config
```python
from flex_cache import init_cache_from_settings
memcache = init_cache_from_settings({'type': 'MemCache'})
diskcache = init_cache_from_settings({'type': 'DiskCache', 
                                      'diskcache_directory': '/tmp'})
rediscache = init_cache_from_settings({'type': 'RedisCache', 
                                       'redis_host': 'redis', 
                                       'redis_username': 'xx', 
                                       'redis_password': 'yy'})
```

### Initialize manually
```python
from redis import Redis
from diskcache import Cache as DCache
from flex_cache import MemCache, DiskCache, RedisCache

memcache = MemCache()
diskcache = DiskCache(DCache())
rediscache = RedisCache(redis_client=Redis(host="redis", decode_responses=True))
```

### Usage
```python
from flex_cache import init_cache_from_settings
cache = init_cache_from_settings({'type': 'MemCache'})
@cache.cache()
def my_func(arg1, arg2):
    result = 123+456  # or some expensive function  
    return result


# Use the function
my_func(1, 2)

# Call it again with the same arguments and it will use cache
my_func(1, 2)

# Invalidate a single value
my_func.invalidate(1, 2)

# Invalidate all values for function
my_func.invalidate_all()
```

## Limitations and things to know
Arguments and return types must be JSON serializable by default. You can override the serializer, but be careful with using Pickle. Make sure you understand the security risks. Pickle should not be used with untrusted values.
https://security.stackexchange.com/questions/183966/safely-load-a-pickle-file

- **ttl** - seconds - based on insertion in the cache - ie. not last access
- **limit** - *ONLY for redis!* limit will revoke keys (once it hits the limit) based on FIFO, not based on LRU

## API
```python
from flex_cache.basecache import BaseCache
from json import loads, dumps
BaseCache(prefix="rc", serializer=dumps, deserializer=loads)

@BaseCache.cache(ttl=None, limit=None, namespace=None)
def cached_func(*args, **kwargs):
    pass  # some costly thing
# Cached function API

# Returns a cached value, if it exists in cache else computes and saves value in cache
cached_func(*args, **kwargs)

# Invalidates a single value
cached_func.invalidate(*args, **kwargs)

# Invalidates all values for cached function
cached_func.invalidate_all()
```

- prefix - The string to prefix the redis keys with
- serializer/deserializer - functions to convert arguments and return value to a string (user JSON by default)
- ttl - The time in seconds to cache the return value
- namespace - The string namespace of the cache. This is useful for allowing multiple functions to use the same cache. By default its `f'{function.__module__}.{function.__file__}'`
