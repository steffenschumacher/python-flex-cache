from json import dumps, loads
from .basecache import BaseCache, BaseCacheDecorator


def get_cache_lua_fn(client):
    if not hasattr(client, '_lua_cache_fn'):
        client._lua_cache_fn = client.register_script("""
local ttl = tonumber(ARGV[2])
local value
if ttl > 0 then
  value = redis.call('SETEX', KEYS[1], ttl, ARGV[1])
else
  value = redis.call('SET', KEYS[1], ARGV[1])
end
local limit = tonumber(ARGV[3])
if limit > 0 then
  local time_parts = redis.call('TIME')
  local time = tonumber(time_parts[1] .. '.' .. time_parts[2])
  redis.call('ZADD', KEYS[2], time, KEYS[1])
  local count = tonumber(redis.call('ZCOUNT', KEYS[2], '-inf', '+inf'))
  local over = count - limit
  if over > 0 then
    local stale_keys_and_scores = redis.call('ZPOPMIN', KEYS[2], over)
    -- Remove the the scores and just leave the keys
    local stale_keys = {}
    for i = 1, #stale_keys_and_scores, 2 do
      stale_keys[#stale_keys+1] = stale_keys_and_scores[i]
    end
    redis.call('ZREM', KEYS[2], unpack(stale_keys))
    redis.call('DEL', unpack(stale_keys))
  end
end
return value
""")
    return client._lua_cache_fn


# Utility function to batch keys
def chunks(iterable, n):
    """Yield successive n-sized chunks from iterator."""
    _iterable = iter(iterable)
    while True:
        elements = []
        for _ in range(n):
            try:
                elements.append(next(_iterable))
            except StopIteration:
                break

        if not len(elements):
            break

        yield elements


class RedisCache(BaseCache):
    def __init__(self, redis_client, prefix="rc", serializer=dumps, deserializer=loads):
        super().__init__(RedisCacheDecorator, redis_client, prefix, serializer, deserializer)

    def mget(self, *fns_with_args):
        keys = self.mget_keys(*fns_with_args)
        results = self._cache.mget(*keys)
        pipeline = self._cache.pipeline()

        deserialized_results = []
        needs_pipeline = False
        for i, result in enumerate(results):
            if result is None:
                needs_pipeline = True

                fn_and_args = fns_with_args[i]
                fn = fn_and_args['fn']
                args = fn_and_args['args'] if 'args' in fn_and_args else []
                kwargs = fn_and_args['kwargs'] if 'kwargs' in fn_and_args else {}
                result = fn.instance.original_fn(*args, **kwargs)
                result_serialized = self.serializer(result)
                get_cache_lua_fn(self._cache)(keys=[keys[i], fn.instance.keys_key], args=[result_serialized, fn.instance.ttl, fn.instance.limit], client=pipeline)
            else:
                result = self.deserializer(result)
            deserialized_results.append(result)

        if needs_pipeline:
            pipeline.execute()
        return deserialized_results


class RedisCacheDecorator(BaseCacheDecorator):
    def __init__(self, redis_client, prefix="rc", serializer=dumps, deserializer=loads, ttl=0, limit=0, namespace=None):
        super().__init__(redis_client, prefix, serializer, deserializer, ttl, limit, namespace)

    def check_cache(self, key):
        return self.cache.get(key)

    def cache_output(self, key, serialized):
        get_cache_lua_fn(self.cache)(keys=[key, self.keys_key], args=[serialized, self.ttl, self.limit])

    def invalidate_key(self, key):
        pipe = self.cache.pipeline()
        pipe.delete(key)
        pipe.zrem(self.keys_key, key)
        pipe.execute()

    def invalidate_all(self, *args, **kwargs):
        chunks_gen = chunks(self.cache.scan_iter(f'{self.prefix}:{self.namespace}:*'), 500)
        for keys in chunks_gen:
            self.cache.delete(*keys)
