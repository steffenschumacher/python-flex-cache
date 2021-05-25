from .rediscache import RedisCache
from .memcache import MemCache
from .diskcache import DiskCache
from .nocache import NoCache

DEFAULT_SETTINGS = {
    'type': 'MemCache',
    'prefix': 'rc',
    'serializer': 'json.dumps',
    'deserializer': 'json.loads',
    'diskcache_directory': None,  # diskcache will default to os specific temp dir
    'redis_host': 'localhost',
    'redis_port': 6379,
    'redis_db': 0,
    'redis_username': None,
    'redis_password': None,
    'redis_clientname': None,
    'redis_ssl_check_hostname': None,
    'redis_decode_responses': True,
}


def _load_func(text):
    from re import match
    m = match(r'^([a-z].*)\.([\w_]+)$', text)
    if not m:
        raise ValueError('\'{}\' is not a valid module.method string?'.format(text))
    module = __import__(m.group(1))
    return getattr(module, m.group(2))


def init_cache_from_settings(settings):
    """
    Initialize a cache using settings dict (see flex_cache.DEFAULT_SETTINGS)
    Args:
        settings:

    Returns:

    """
    merged = DEFAULT_SETTINGS.copy()
    merged.update(settings)
    common_kwargs = {'prefix': merged['prefix'],
                     'serializer': _load_func(merged['serializer']),
                     'deserializer': _load_func(merged['deserializer']),
                     }
    if merged['type'] == 'MemCache':
        return MemCache(**common_kwargs)
    elif merged['type'] == 'DiskCache':
        from diskcache import Cache as DCache
        dc = DCache(directory=merged['diskcache_directory'])
        return DiskCache(dc, **common_kwargs)
    elif merged['type'] == 'RedisCache':
        redis_kwargs = {k[6:]: v for k, v in common_kwargs.items() if k.startswith('redis')}
        from redis import Redis
        client = Redis(**redis_kwargs)
        return RedisCache(client, **common_kwargs)
    elif merged['type'] == 'NoCache':
        return NoCache()
    else:
        raise ValueError('Unsupported caching type: {}'.format(merged['type']))
