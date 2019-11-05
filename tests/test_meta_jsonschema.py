
import uuid
import names
import pytest
import time
from store.database import Store


@pytest.fixture(scope="module")
def t():
    class Cat(Store):
        meta = {
            "schema_version": "v2",
            "schema_type": "jsonschema"
        }
        schema = {
            "v1": {
                'type': 'object',
                'properties': {
                    'title': {'type': 'string'},
                    'user': {'type': 'string'},
                    'content': {'type': 'string'},
                    'likes': {'type': 'integer'},
                }
            },
            "v2": {
                'type': 'object',
                'properties': {
                    'title': {'type': 'string'},
                    'user': {'type': 'string'},
                    'content': {'type': 'string'},
                    'likes': {'type': 'integer'},
                }
            },
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
        'content': 'hello world',
        'likes': 123
    })
    assert t[n][0].user == 'dameng'
    assert t[n][0].content == 'hello world'

# def test_update_meta(t):
#     t.update_meta('likes=123', 'hello', 'world')
#     es = t['likes=123']
#     print(es)

# def test_delete_meta(t):
#     t.delete_meta('likes=123', 'hello')
#     es = t['likes=123']
#     print(es)

def xtest_all(t):
    print(t['*'])