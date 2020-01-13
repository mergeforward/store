
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


def test_nomal_should_be_added(t):
    # t.update({"likes": 123}, {"user": "meng2"}, patch=True)
    n = t.create('1', {
        'title': '每日新闻 2019.08.06',
        'user': 'meng',
        'content': 'hello world',
        'likes': 123,
        'archive': False,
        'l': ["a", "b", "c", "dameng"],
        'extra': {
            'l': ["a", "b", "c", "dameng"],
            "a": "1",
            "b": "2",
            "c": {
                "nest": "what3!",
                "n1": 12,
                "n2": "12"
            },
            "d": ["aa", "bb", "ab"]
        }
    }, update=True)
    # assert t[n][0].user == 'meng'
    # assert t[n][0].content == 'hello world'

def test_search(t):
    # es = t.search({"user": "meng", "likes": 456})
    # es = t.search({"likes": {"op": ">", "val": 100}}, debug=True)
    # es, total = t.search({"extra.c.n2": {"op": "=", "val": "12"}}, debug=True)
    
# SELECT `e`.`id`, `e`.`create`, `e`.`update`, `e`.`key`, `e`.`data`, `e`.`meta`
# FROM `article` `e`
# WHERE (
# (json_contains(`e`.`data`, %s, %s) or json_contains_path(`e`.`data`, 'one', %s)) OR 
# (json_contains(`e`.`data`, %s, %s) or json_contains_path(`e`.`data`, 'one', %s)) OR 
# (json_contains(`e`.`data`, %s, %s) or json_contains_path(`e`.`data`, 'one', %s)))
# ORDER BY `e`.`update` DESC, `e`.`id` DESC

# ----sql----
# SELECT "e"."id", "e"."create", "e"."update", "e"."key", "e"."data", "e"."meta"
# FROM "article" "e"
# WHERE (
# ("e"."data" #> %(p1)s) ? %(p2)s OR 
# ("e"."data" #> %(p1)s) ? %(p4)s OR 
# ("e"."data" #> %(p1)s) ? %(p6)s)
# ORDER BY "e"."update" DESC, "e"."id" DESC
# -----------




    # es, total = t.search({"d": {"op": "in", "val": ["da","aa"], "pa": "extra"}}, debug=True)
    es, total = t.search({"extra.d": {"op": "ain", "val": ["ab", "aa"]}}, debug=True)
    # es, total = t.search({"l": {"op": "in", "val": "me"}}, debug=True)
    # es, total = t.search({"user": ["a", "me", "meng"]}, debug=True)
    # es, total = t.search({"l":"da"}, debug=True)
    # es, total = t.search({"extra.c.n1": {"op": "=", "val": 12}}, debug=True, begin=0, end=1, mode='normal')
    # es = t.search({"archive": False}, fuzzy=False, debug=True)
    # es = t.search({"user": "meng"}, fuzzy=False, debug=True)
    # es = t.search({"extra.c.n2": 456.7}, debug=True)
    # es = t.search({"likes": 123}, debug=True)
    # es = t.search({"extra.c.nest": 'what'}, debug=True)
    # es = t.search({"extra.c.nest": 'what3!'}, fuzzy=False, debug=True)
    # es = t.search({"user": "meng", "extra.c.n2": 456.7})
    # es = t.search({"extra.c.n2": ["456", "12"]}, debug=True)
    # es = t.search({"likes": [123, "12"]}, debug=True)
    # es = t.search({"archive": False}, fuzzy=False, debug=True)
    # es = t.search({"likes": 123}, fuzzy=False, debug=True)
    # es = t.search({"likes": [456, 12]}, debug=True)
    print('-'*40)
    for e in es:
        print(e)
    print(total)

def xtest_delete(t):
    t.delete({"user": "meng"})
    es,total = t.search({"user": "meng"}, debug=True)
    print(es)
# def test_delete_meta(t):
#     t.delete_meta('likes=123', 'hello')
#     es = t['likes=123']
#     print(es)

def xtest_all(t):
    print('........')
    print(t['*'])