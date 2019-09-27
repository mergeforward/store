import uuid
import names
import pytest
import time
from store.database import Store


@pytest.fixture(scope="module")
def t():
    class Cat(Store):
        provider='mysql'
        port=8306 
        password='dangerous123'
        database='mytest'
        user='root'
    return Cat() 


def test_add_article_should_find_matched_by_user_name(t):
    del t['user=dameng']
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


def test_set_get_multi_form_should_return_as_expected(t):
    t.a = 1   
    t.b = 1.1  
    t.c = 'hello world'
    t.d = ['hello', 'world']
    t.e = {'hello': 'world'}

    assert t.a.data == 1
    assert t.b.data == 1.1
    assert t.c.data == 'hello world'
    assert t.d.data == ['hello', 'world']
    assert t.e.data == {'hello': 'world'}

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


def test_query_keys_existence(t):
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
    for elem in t['a.b.c?']:
        assert elem['a']['b']['c'] == 123

    del t.a
    del t.b
    
def xtest_insert_many(t):
    a = time.time()
    for i in range(10000, 20000):
        t[f's_{i}'] = {
            "type": "image",
            "resource": str(uuid.uuid1()),
            "fname": names.get_first_name(),
            "lname": names.get_last_name()
        }
        if i % 200 == 0:
            print('{} inserted'.format(i))
            b = time.time()
            print('insert>', b-a)
    print('inserted', b-a)


def test_query_by_name(t):
    a = time.time()
    e = t['fname=Mark']
    print(len(e), len(t))
    b = time.time()
    print(b-a)
    assert b-a>0


if __name__ == "__main__":
    class Cat(Store):
        pass
    t= Cat(provider='mysql', port=8306, password='dangerous123', database='mytest', user='root')
    a = time.time()
    e = t['fname=Mark']
    print()
    print(len(t))
    print(len(e))
    b = time.time()
    print(b-a)
