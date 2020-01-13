
import uuid
import names
import pytest
import time
from store.database import Store, StoreException


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
                    'extra': {'type': 'object'},
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


def test_update_meta_schema_failed(t):
    n = t.add({
        'title': '每日新闻 2019.08.06',
        'user': 'dameng',
        'content': 'hello world',
        'likes': 123,
        'extra': {"hello": "world"}
    })
    assert t[n][0].user == 'dameng'
    assert t[n][0].content == 'hello world'
    elem = t[n][0]
    with pytest.raises(StoreException) as e:
        elem.update_meta_multi({'schema_version': "v2"})

def test_update_data_nest(t):
    # with pytest.raises(StoreException) as e:
    t.update({'user': 'dameng'}, {"extra": {"a": "b"}}, patch='nest')
    es,_ = t.search({'user': 'dameng'})
    for e in es:
        assert "a" in e.extra
        assert "hello" in e.extra

# def test_delete_meta(t):
#     t.delete_meta('likes=123', 'hello')
#     es = t['likes=123']
#     print(es)

def xtest_all(t):
    print(t['*'])