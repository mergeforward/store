
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
        # provider='postgres'
        # port=5432 
        provider='mysql'
        port=3306 
        password='dangerous123'
        database='mytest'
        user='root'
    return Article() 


def test_nomal_should_be_added(t):
    n = t.create('c1', {
        'title': 'news01',
        'user': 'meng',
        'content': 'hello01',
        'likes': 121,
    }, update=True)
    n = t.create('c2', {
        'title': 'news02',
        'user': 'zhang',
        'content': 'hello02',
        'likes': 123,
    }, update=True)

def test_search(t):
    print('-'*40)
    print(t)
    es,_ = t.search_multi([{
        'title': 'news01',
        'user': 'meng'
    },{
        'title': 'news02',
        'user': 'zhang'
    }], fuzzy=False)
    print(es)
