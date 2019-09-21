import uuid
import names
import pytest
import time
from store.database import Store


@pytest.fixture(scope="module")
def t():
    class Cat(Store):
        pass
    return Cat(provider='mysql', port=8306, password='dangerous123', database='mytest', user='root')
    # return Cat(provider='postgres', user='dameng', password='pythonic', database='mytest')


def test_add_article(t):
    t.add({
        'title': '每日新闻 2019.08.06',
        'user': 'dameng',
        'content': 'hello world'
    })

    t.add({
        'title': '每日新闻 2019.08.05',
        'user': 'dameng',
        'content': 'hello world'
    })

    elems = t['user=dameng']
    for elem in elems:
        assert elem['user'] == 'dameng'
    
    assert len(elems) == 2

    del t['user=dameng']

    assert len(t['user=dameng']) == 0


def xtest_set_get(t):
    t.a = 1   
    t.b = 1.1  
    t.c = 'hello world'
    t.d = ['hello', 'world']
    t.e = {'hello': 'world'}

    assert t.a.value == 1
    assert t.b.value == 1.1
    assert t.c.value == 'hello world'
    assert t.d.value == ['hello', 'world']
    assert t.e.value == {'hello': 'world'}

    del t.a
    del t.b
    del t.c
    del t.d
    del t.e

    assert t.a == None
    assert t.b == None
    assert t.c == None
    assert t.d == None
    assert t.e == None


def test_query_keys(t):
    t.a = {
        'a': {
            'b': {
                'c': 123
            }
        }
    }
    t.b = {
        'a': {
            'b': {
                'c': 123
            }
        }
    }
    print(t['a.b.c?'])
    # for elem in t['a.b.c?']:
    #     assert elem['a']['b']['c'] == 123

    # del t.a
    # del t.b
    
def xtest_insert_many(t):
    a = time.time()
    for i in range(1000):
        t[f's_{i}'] = {
            "type": "image",
            "resource": str(uuid.uuid1()),
            "fname": names.get_first_name(),
            "lname": names.get_last_name()
        }
        if i % 100 == 0:
            print('{} inserted'.format(i))
            b = time.time()
            print('insert>', b-a)
    print('inserted', b-a)


def test_query_many(t):
    a = time.time()
    e = t['fname=Mark']
    print(len(e))
    b = time.time()
    print(b-a)
