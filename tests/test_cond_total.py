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
    return Fish(begin=0,end=1) 


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

    t.add({
        'title': '每日新闻 2019.09.05',
        'user': 'zoey',
        'content': 'hello world'
    })

    elems = t['user=dameng']
    for elem in elems:
        assert elem['user'] == 'dameng'

    # assert len(elems) == 2

    assert t.count('user=dameng') == 2

    del t['user=dameng']

    assert len(t['user=dameng']) == 0

