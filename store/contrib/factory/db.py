
from copy import copy
from store.database import Store


class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class StoreFactory(metaclass=Singleton):
    def __init__(self, *args, **kwargs):
        self.store = {}
        self.kwargs = kwargs
    def make(self, classname, **kwargs):
        if classname in self.store.keys():
            return self.store[classname]
        copied_kwargs = copy(self.kwargs)
        if kwargs and isinstance(kwargs, dict):
            copied_kwargs.update(kwargs)
        copied_kwargs['__metaclass__'] = Singleton
        store_class = type(classname, (Store, ),  copied_kwargs)
        self.store[classname] = store_class
        return store_class


if __name__ == "__main__":
    fac = StoreFactory( 
        provider="mysql", 
        host="127.0.0.1", port=8306, 
        database="mytest",
        user="root", 
        password="dangerous123", 
        schema = {
            'title': {'type': 'string'},
            'user': {'type': 'string'},
            'content': {'type': 'string'},
            'likes': {'type': 'integer'},
        }
    )
    s = fac.make("Address")
    s = s()
    s.a = {'title': 'world'}
    print(s.a)