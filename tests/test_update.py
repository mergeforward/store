import uuid
import names
import pytest
import time
from store.database import Store


@pytest.fixture(scope="module")
def t():
    class Dog(Store):
        provider='mysql'
        port=3306 
        # provider='postgres'
        # port=5432 
        password='dangerous123'
        database='mytest'
        user='root'
    return Dog() 


def test_update(t):
    del t['user=dameng']
    t.add({
        'title': '每日新闻 2019.08.06',
        'user': 'dameng',
        'content': 'hello world'
    })

    es = t['user=dameng']
    es['content'] = 'helloworld'
    rc = t['user=dameng']
    assert rc['content'] == ['helloworld']

    del t['user=dameng']

    assert len(t['user=dameng']) == 0


def test_update_nested(t):
    del t['dameng?']
    t.add({
        'dameng': {
            'title': '每日新闻 2019.08.06',
            'content': 'hello world'
        },
    })

    es = t['dameng?']
    es['dameng.content'] = 'amazing!'
    rc = t['dameng?']

    assert rc['dameng.content'] == ['amazing!']
    del t['dameng?']

    assert len(t['dameng?']) == 0