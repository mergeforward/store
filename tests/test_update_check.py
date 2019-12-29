
import uuid
import names
import pytest
import time
from store.database import Store


@pytest.fixture(scope="module")
def t():
    class CatUpdate(Store):
        meta = {
            "schema_version": "v1",
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
                    'likes': {'type': 'string'},
                }
            },
        }
        provider='mysql'
        port=3306 
        password='dangerous123'
        database='mytest'
        user='root'
    return CatUpdate() 


def test_nomal_should_be_added(t):
    n = t.add({
        'title': '每日新闻 2019.08.06',
        'user': 'dameng',
        'content': 'hello world',
        'likes': 123
    })
    assert t[n][0].user == 'dameng'
    assert t[n][0].content == 'hello world'
    e = t[n][0]
    try:
        e.update_meta_multi({'schema_version': "v2"})
    except Exception as e:
        print('.'*40)
        print(e)
        print(type(e))

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