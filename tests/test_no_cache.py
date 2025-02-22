import uuid
import time

from flex_cache import NoCache

import pickle
import pytest
import zlib


@pytest.fixture(scope="session", autouse=True)
def clear_cache(request):
    pass


@pytest.fixture()
def cache():
    return NoCache()


def add_func(n1, n2):
    """ Add function
    Add n1 to n2 and return a uuid4 unique verifier

    Returns:
        tuple(int, str(uuid.uuid4))
    """
    return n1 + n2, str(uuid.uuid4())


def test_basic_check(cache):
    @cache.cache()
    def add_basic(arg1, arg2):
        return add_func(arg1, arg2)

    r_3_4, v_3_4 = add_basic(3, 4)
    r_3_4_cached, v_3_4_cached = add_basic(3, 4)
    r_5_5, v_5_5 = add_basic(5, 5)

    assert 7 == r_3_4 == r_3_4_cached and v_3_4 != v_3_4_cached
    assert 10 == r_5_5 and v_5_5 != r_3_4


def test_ttl(cache):
    @cache.cache(ttl=1)
    def add_ttl(arg1, arg2):
        return add_func(arg1, arg2)

    r_1, v_1 = add_ttl(3, 4)
    r_2, v_2 = add_ttl(3, 4)
    time.sleep(2)

    r_3, v_3 = add_ttl(3, 4)

    assert 7 == r_1 == r_2 == r_3
    assert v_1 != v_2 != v_3


def test_invalidate_not_in_cache(cache):
    @cache.cache()
    def add_invalidate_not_in_cache(arg1, arg2):
        return add_func(arg1, arg2)

    r_3_4, v_3_4 = add_invalidate_not_in_cache(3, 4)
    r_4_4, v_4_4 = add_invalidate_not_in_cache(4, 4)

    # calling invalidate with params that was never
    # passed should not change the cache status
    add_invalidate_not_in_cache.invalidate(5, 5)

    r2_3_4, v2_3_4 = add_invalidate_not_in_cache(3, 4)
    r2_4_4, v2_4_4 = add_invalidate_not_in_cache(4, 4)

    assert r_3_4 == r2_3_4 and v_3_4 != v2_3_4
    assert r_4_4 == r2_4_4 and v_4_4 != v2_4_4


def test_invalidate_in_cache(cache):
    @cache.cache()
    def add_invalidate_in_cache(arg1, arg2):
        return add_func(arg1, arg2)

    r_3_4, v_3_4 = add_invalidate_in_cache(3, 4)
    r_4_4, v_4_4 = add_invalidate_in_cache(4, 4)

    # we are invalidating 4, 4 so it should be re-executed next time
    add_invalidate_in_cache.invalidate(4, 4)

    r2_3_4, v2_3_4 = add_invalidate_in_cache(3, 4)
    r2_4_4, v2_4_4 = add_invalidate_in_cache(4, 4)

    assert r_3_4 == r2_3_4 and v_3_4 != v2_3_4
    # 4, 4 was invalidated a new verifier should be generated
    assert r_4_4 == r2_4_4 and v_4_4 != v2_4_4


def test_invalidate_all():
    cache = NoCache()

    @cache.cache()
    def f1_invalidate_all(arg1, arg2):
        return add_func(arg1, arg2)

    @cache.cache()
    def f2222_invalidate_all(arg1, arg2):
        return add_func(arg1, arg2)

    r_3_4, v_3_4 = f1_invalidate_all(3, 4)
    r_4_4, v_4_4 = f1_invalidate_all(4, 4)
    r_5_5, v_5_5 = f2222_invalidate_all(5, 5)

    # invalidating all caches to the function f1_invalidate_all
    f1_invalidate_all.invalidate_all()

    r2_3_4, v2_3_4 = f1_invalidate_all(3, 4)
    r2_4_4, v2_4_4 = f1_invalidate_all(4, 4)
    r2_5_5, v2_5_5 = f2222_invalidate_all(5, 5)

    # all caches related to f1_invalidate_all were invalidated
    assert r_3_4 == r2_3_4 and v_3_4 != v2_3_4
    assert r_4_4 == r2_4_4 and v_4_4 != v2_4_4

    # caches of f2222_invalidate_all should not stay stored
    assert r_5_5 == r2_5_5 and v_5_5 != v2_5_5


class Result:
    def __init__(self, arg1, arg2):
        self.sum = arg1 + arg2
        self.verifier = str(uuid.uuid4())


class Arg:
    def __init__(self, value):
        self.value = value


def test_custom_serializer():
    cache = NoCache(serializer=pickle.dumps, deserializer=pickle.loads)

    @cache.cache()
    def add_custom_serializer(arg1, arg2):
        return Result(arg1.value, arg2.value)

    r1 = add_custom_serializer(Arg(2), Arg(3))
    r2 = add_custom_serializer(Arg(2), Arg(3))

    assert r1.sum == r2.sum and r1.verifier != r2.verifier


def test_custom_serializer_with_compress():
    def dumps(value):
        return zlib.compress(pickle.dumps(value))

    def loads(value):
        return pickle.loads(zlib.decompress(value))

    cache = NoCache(serializer=dumps, deserializer=loads, )

    @cache.cache()
    def add_compress_serializer(arg1, arg2):
        return Result(arg1.value, arg2.value)

    r1 = add_compress_serializer(Arg(2), Arg(3))
    r2 = add_compress_serializer(Arg(2), Arg(3))

    assert r1.sum == r2.sum and r1.verifier != r2.verifier


def test_basic_mget(cache):
    try:
        @cache.cache()
        def add_basic_get(arg1, arg2):
            return add_func(arg1, arg2)

        r1_3_4, v1_3_4 = add_basic_get(3, 4)
        cache.mget({"fn": add_basic_get, "args": (3, 4)})[0]
        pytest.fail('NoCache does not support mget')
    except NotImplementedError as nie:
        pass


def test_basecache_setget(cache):
    cache.set('setget', 'basic', namespace='base')
    assert cache.get('setget', namespace='base') is None


def test_basecache_invalidate(cache):
    cache.set('setget', 'basic', ttl=3600, namespace='base')
    cache.invalidate('setget', namespace='base')
    assert cache.get('setget', namespace='base') is None
