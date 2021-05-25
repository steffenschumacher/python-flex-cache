from functools import wraps
from json import dumps, loads
from base64 import b64encode


class BaseCache:
    def __init__(self, decorator, cache, prefix="rc", serializer=dumps, deserializer=loads):
        self._decorator = decorator
        self._cache = cache
        self.prefix = prefix
        self.serializer = serializer
        self.deserializer = deserializer

    def cache(self, ttl=0, limit=0, namespace=None):
        return self._decorator(self._cache, self.prefix, self.serializer, self.deserializer, ttl, limit, namespace)

    def mget_keys(self, *fns_with_args):
        keys = []
        for fn_and_args in fns_with_args:
            fn = fn_and_args['fn']
            args = fn_and_args['args'] if 'args' in fn_and_args else []
            kwargs = fn_and_args['kwargs'] if 'kwargs' in fn_and_args else {}
            keys.append(fn.instance.get_key(args=args, kwargs=kwargs))
        return keys

    def mget(self, *fns_with_args):
        raise NotImplementedError('Must be implemented in derived classes')

    def _key(self, key, namespace=None):
        if not isinstance(key, str):
            key = str(b64encode(key), 'utf-8')
        if namespace:
            return f'{self.prefix}:{namespace}:{key}'
        else:
            return f'{self.prefix}:{key}'

    def get(self, key, namespace=None):
        serialized = self.cache(namespace=namespace).check_cache(self._key(key, namespace))
        if serialized:
            return self.deserializer(serialized)
        else:
            return None

    def set(self, key, value, ttl=0, limit=0, namespace=None):
        serialized = self.serializer(value)
        deco = self.cache(ttl, limit, namespace)
        deco.keys_key = self._key('keys', namespace=namespace)
        return deco.cache_output(self._key(key, namespace), serialized)

    def invalidate(self, key, namespace=None):
        deco = self.cache(namespace=namespace)
        deco.keys_key = self._key('keys', namespace=namespace)
        deco.invalidate_key(self._key(key, namespace))


class BaseCacheDecorator:
    def __init__(self, cache, prefix='rc', serializer=dumps, deserializer=loads, ttl=0, limit=0, namespace=None):
        self.cache = cache
        self.prefix = prefix
        self.serializer = serializer
        self.deserializer = deserializer
        self.ttl = ttl
        self.limit = limit
        self.namespace = namespace
        self.keys_key = None

    def get_key(self, args, kwargs):
        serialized_data = self.serializer([args, kwargs])

        if not isinstance(serialized_data, str):
            serialized_data = str(b64encode(serialized_data), 'utf-8')
        return f'{self.prefix}:{self.namespace}:{serialized_data}'

    def __call__(self, fn):
        self.namespace = self.namespace if self.namespace else f'{fn.__module__}.{fn.__name__}'
        self.keys_key = f'{self.prefix}:{self.namespace}:keys'
        self.original_fn = fn

        @wraps(fn)
        def inner(*args, **kwargs):
            nonlocal self
            key = self.get_key(args, kwargs)
            result = self.check_cache(key)
            if not result:
                result = fn(*args, **kwargs)
                result_serialized = self.serializer(result)
                self.cache_output(key, result_serialized)
            else:
                result = self.deserializer(result)
            return result

        inner.invalidate = self.invalidate
        inner.invalidate_all = self.invalidate_all
        inner.instance = self
        return inner

    def check_cache(self, key):
        raise NotImplementedError('Must be implemented in derived classes')

    def cache_output(self, key, serialized):
        raise NotImplementedError('Must be implemented in derived classes')

    def invalidate_key(self, key):
        raise NotImplementedError('Must be implemented in derived classes')

    def invalidate(self, *args, **kwargs):
        key = self.get_key(args, kwargs)
        self.invalidate_key(key)
        if key in self.cache:
            self.invalidate_key(key)

    def invalidate_all(self, *args, **kwargs):
        if not self.namespace or not self.cache:
            return
        key_prefix = f'{self.prefix}:{self.namespace}:'
        for k in [k for k in self.cache if k.startswith(key_prefix)]:
            self.invalidate_key(k)

