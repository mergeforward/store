import uuid
import names
import pytest
import time
from store.database import Store


@pytest.fixture(scope="module")
def t():
    class Cat(Store):
        provider='mysql'
        port=3306 
        # provider='postgres'
        # port=5432 
        password='dangerous123'
        database='mytest'
        user='root'
    return Cat() 


    
def xtest_insert_many(t):
    a = time.time()
    for i in range(00000, 10000):
    # for i in range(10000, 20000):
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

