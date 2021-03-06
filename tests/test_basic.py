import uuid
import names
import pytest
import time
from store.database import Store


@pytest.fixture(scope="module")
def t():
    class Fish(Store):
        provider='postgres'
        provider='mysql'
        port=3306 
        # port=5432 
        password='dangerous123'
        database='mytest'
        user='root'
    return Fish() 


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

def test_0001_like_data(t):
    t.stu_0001 ={
        'id': '0001',
        'name': 'xiaoming'
    }
    t.stu_0002 ={
        'id': '0002',
        'name': 'xiaochao'
    }
    elems = t['id=0001']
    del t.stu_0001
    del t.stu_0002
    
def test_array_data(t):
    t.array ={
        'data': [{'id': '0001'}, {'id': '0002'}]
    }
    elems = t['data.*.id=0001']
    # print(elems)
    del t.array
    del t.aaa
    del t['a=b']
    # print('^'*40)

if __name__ == "__main__":
    # class Cat(Store):
    #     pass
    # # t= Cat(provider='mysql', port=8306, password='dangerous123', database='mytest', user='root')
    # t = Cat(provider='postgres', port=5432, password='dangerous123', database='mytest', user='root')
    class Cat(Store):
        provider='postgres'
        # provider='mysql'
        # port=8306 
        port=5432 
        password='dangerous123'
        database='mytest'
        user='root'
    t= Cat() 
    a = time.time()
    e = t['fname=Mark']
    print()
    print(len(t))
    print(len(e))
    b = time.time()
    print(b-a)
