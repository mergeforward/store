
import uuid
import names
import pytest
import time
from store.database import Store


@pytest.fixture(scope="module")
def t():
    class Article(Store):
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
            },
        }
        provider='postgres'
        port=5432 
        # provider='mysql'
        # port=3306 
        password='dangerous123'
        database='mytest'
        user='root'
    return Article() 


def xtest_nomal_should_be_added(t):
    n = t.add({
        'title': '每日新闻 2019.08.06',
        'user': 'meng',
        'content': 'hello world',
        'likes': 123,
        'archive': False,
        'l': ["a", "b", "c"],
        'extra': {
            "a": "1",
            "b": "2",
            "c": {
                "nest": "what3!",
                "n2": "12"
            },
            "d": ["aa", "bb", "ab"]
        }
    })
    assert t[n][0].user == 'meng'
    assert t[n][0].content == 'hello world'

def test_search(t):
    # es = t.search({"user": "meng", "likes": 456})
    # es = t.search({"likes": 123.1})
    # es = t.search({"user": "me"})
    # es = t.search({"extra.c.n2": 456.7})
    # es = t.search({"extra.c.nest": 'what2'})
    # es = t.search({"user": "meng", "extra.c.n2": 456.7})
    es = t.search({"extra.c.n2": [456, "12"]})
    print('-'*40)
    print(es)

# def test_delete_meta(t):
#     t.delete_meta('likes=123', 'hello')
#     es = t['likes=123']
#     print(es)

def xtest_all(t):
    print('........')
    print(t['*'])