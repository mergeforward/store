
import uuid
import names
import pytest
import time
from store.database import Store


@pytest.fixture(scope="module")
def t():
    class Cat(Store):
        schema = {
            'title': {'type': 'string', 'required': True},
            'user': {'type': 'string', 'required': True},
            'content': {'type': 'string', 'required': True},
            'likes': {'type': 'integer', 'required': False},
        }
        provider='mysql'
        port=3306 
        password='dangerous123'
        database='mytest'
        user='root'
    return Cat() 


def test_nomal_should_be_added(t):
    n = t.add({
        'title': '每日新闻 2019.08.06',
        'user': 'dameng',
        'content': 'hello world'
    })
    assert t[n][0].user == 'dameng'
    assert t[n][0].content == 'hello world'

