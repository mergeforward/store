import json
import os
import uuid
from copy import copy
from datetime import datetime

from pony.orm import (Database, Json, PrimaryKey, Required, commit, count,
                      db_session, delete, desc, select)
from store.parser import parse

class StoreMetas:
    def __init__(self, elems, store=None):
        if not elems:
            elems = []
        self.elems = [StoreMeta(elem, store=store) for elem in elems]

    def __str__(self):
        return '\n'.join([str(elem) for elem in self.elems])

    def __len__(self):
        return len(self.elems)

    @db_session
    def __getitem__(self, key):
        if isinstance(key, int):
            return self.elems[key]
        if isinstance(key, slice):
            return self.elems[key]
        return [elem[key] for elem in self.elems]

    @db_session
    def __setitem__(self, key, value):
        if isinstance(key, int):
            self.elems[key] = value
            return
        for elem in self.elems:
            elem[key] = value


    @db_session
    def __getattribute__(self, key):
        if key in ['elems'] or key.startswith('_'):
            return object.__getattribute__(self, key)

        if key == 'store':
            return [elem.store for elem in self.elems]
        if key == 'id':
            return [elem.id for elem in self.elems]
        if key == 'key':
            return [elem.key for elem in self.elems]
        if key == 'value':
            return [elem.value for elem in self.elems]
        if key == 'create':
            return [elem.create for elem in self.elems]
        if key == 'update':
            return [elem.update for elem in self.elems]
        return [elem[key] for elem in self.elems]


class StoreMeta:
    def __init__(self, elem, store=None):
        self.store = store
        self.id = elem.id
        self.key = elem.key
        self.value = elem.value
        self.create = elem.create.strftime("%Y-%m-%dT%H:%M:%S")
        self.update = elem.update.strftime("%Y-%m-%dT%H:%M:%S")

    def __str__(self):
        return "id: {}, key: {}, value: {}, create: {}, update: {}".format(self.id, self.key, self.value, self.create, self.update)

    @db_session
    def __assign__(self, value):
        elem = select(e for e in self.store if e.id == self.id).for_update().first()
        if elem is None:
            raise Exception('elem not found')
        else:
            elem.value = value
            elem.update = datetime.utcnow()

            self.value = elem.value
            self.update = elem.update.strftime("%Y-%m-%dT%H:%M:%S")

    @db_session
    def __setattr__(self, key, value):
        if key in ['store', 'id', 'key', 'value', 'create', 'update'] or key.startswith('_'):
            return super().__setattr__(key, value)
        elem = select(e for e in self.store if e.id == self.id).for_update().first()
        if elem is None:
            raise Exception('elem not found')
        else:
            if isinstance(elem.value, dict):
                elem.value[key] = value
                elem.update = datetime.utcnow()

                self.value = elem.value
                self.update = elem.update.strftime("%Y-%m-%dT%H:%M:%S")
            else:
                raise Exception('value not dict!')

    @db_session
    def __getattribute__(self, key):
        if key in ['store', 'id', 'key', 'value', 'create', 'update'] or key.startswith('_'):
            return object.__getattribute__(self, key)

        elem = select(e for e in self.store if e.id == self.id).first()
        if elem:
            if isinstance(elem.value, dict):
                return elem.value.get(key)

    @db_session
    def __setitem__(self, key, value):
        elem = select(e for e in self.store if e.id == self.id).for_update().first()
        if elem is None:
            raise Exception('elem not found')
        else:
            if isinstance(elem.value, dict) or \
               (isinstance(key, int) and isinstance(elem.value, list)):
                elem.value[key] = value
                elem.update = datetime.utcnow()

                self.value = elem.value
                self.update = elem.update.strftime("%Y-%m-%dT%H:%M:%S")
            else:
                raise Exception('value not dict!')

    @db_session
    def __getitem__(self, key):
        elem = select(e for e in self.store if e.id == self.id).first()
        if elem:
            if isinstance(elem.value, dict) or \
               (isinstance(key, int) and isinstance(elem.value, list)) or \
               (isinstance(key, int) and isinstance(elem.value, str)):
                if isinstance(key, int):
                    return elem.value[key]
                else:
                    return elem.value.get(key)
class Store(object):
    _safe_attrs = ['store', 'database', 'tablename', 
                   'begin', 'end', 'order', 
                   'add', 'register_attr', 'slice', 'adjust_slice', 'provider',
                   'query_key', 'count', 'desc', 'asc',
                   'provider', 'user', 'password', 'host', 'port', 'database', 'filename'
                   ]

    provider = 'sqlite'
    user = 'test'
    password = 'test'
    host = 'localhost'
    port = 5432
    database = 'test'
    filename = 'database.sqlite'
    order = 'desc'

    def __init__(self,
                 provider=None, user=None, password=None,
                 host=None, port=None, database=None, filename=None,
                 begin=None, end=None, order=None):
        if not provider:
            provider = self.provider

        if provider == 'sqlite':
            if not filename:
                filename = self.filename 
            if not filename.startswith('/'):
                filename = os.getcwd()+'/' + filename
            self.database = Database(
                provider=provider, 
                filename=filename, 
                create_db=True)
        else:
            self.database = Database(
                provider=provider, 
                user=user or self.user, 
                password=password or self.password,
                host=host or self.host, 
                port=port or self.port, 
                database=database or self.database)

        self.provider = provider

        self.begin, self.end = begin, end
        self.order = order or self.order
        self.tablename = self.__class__.__name__

        schema = dict(
            id=PrimaryKey(int, auto=True),
            create=Required(datetime, sql_default='CURRENT_TIMESTAMP', default=lambda: datetime.utcnow()),
            update=Required(datetime, sql_default='CURRENT_TIMESTAMP', default=lambda: datetime.utcnow()),
            key=Required(str, index=True, unique=True),
            value=Required(Json, volatile=True)
        )

        self.store = type(self.tablename, (self.database.Entity,), schema)
        self.database.generate_mapping(create_tables=True, check_tables=True)

    def slice(self, begin, end):
        self.begin, self.end = begin, end

    def desc(self):
        self.order = 'desc'

    def asc(self):
        self.order = 'asc'

    @staticmethod
    def register_attr(name):
        if isinstance(name, str) and name not in Store._safe_attrs:
            Store._safe_attrs.append(name)

    @db_session
    def __setattr__(self, key, value):
        if key in Store._safe_attrs or key.startswith('_'):
            return super().__setattr__(key, value)
        item = select(e for e in self.store if e.key == key).first()
        if item is None:
            self.store(key=key, value=value)
        else:
            item.value = value
            item.update = datetime.utcnow()

    @db_session
    def __getattribute__(self, key):
        if key in Store._safe_attrs or key.startswith('_'):
            return object.__getattribute__(self, key)

        elem = select(e for e in self.store if e.key == key).first()
        if elem:
            return StoreMeta(elem, store=self.store)
        return None

    @db_session
    def count(self, key):
        if isinstance(key, slice):
            raise Exception('not implemented!')
        elif isinstance(key, tuple):
            key='.'.join(key)

        # string key
        filters = parse(key)
        elems = select(e for e in self.store)
        if filters:
            elems = elems.filter(filters)
        return elems.count()

    @db_session
    def __getitem__(self, key):
        if isinstance(key, slice):
            raise Exception('not implemented!')
        elif isinstance(key, tuple):
            key='.'.join(key)

        # string key
        filters = parse(key)
        # print('filter:', filters)
        elems = select(e for e in self.store)
        if filters:
            elems = elems.filter(filters)
        if self.order == 'desc':
            elems = elems.order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id))
        elems = self.adjust_slice(elems, for_update=False)
        return StoreMetas(elems, store=self.store)


    @db_session
    def __setitem__(self, key, value):

        if isinstance(key, slice):
            raise Exception('not implemented!')
        elif isinstance(key, tuple):
            key='.'.join(key)
        
        filters = parse(key)
        elems = select(e for e in self.store)
        if filters:
            elems = elems.filter(filters)
        if self.order_by == 'desc':
            elems = elems.order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id))
        elems = self.adjust_slice(elems, for_update=True)
        if elems:
            now = datetime.utcnow()
            for elem in elems:
                elem.value = value
                elem.update = now
        else:
            if key.isidentifier():
                return self.__setattr__(key, value)
            raise Exception('Not Implemented!')
        return

        

            

    @db_session
    def __delitem__(self, key):
        if isinstance(key, slice):
            raise Exception('not implemented!')
        elif isinstance(key, tuple):
            key = '.'.join(key)
        filters = parse(key)
        elems = select(e for e in self.store)
        if filters:
            elems = elems.filter(filters)
        if self.order_by == 'desc':
            elems = elems.order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id))
        if elems:
            for elem in elems:
                elem.delete()
        return
       

    @db_session
    def __delattr__(self, key):
        delete(e for e in self.store if e.key == key)


    @db_session
    def add(self, value):
        hex = uuid.uuid1().hex
        key = "store_{}".format(hex)
        self.store(key=key, value=value)
        return key

    @db_session
    def _query_key(self, key, for_update=False):
        if for_update:
            return select(e for e in self.store if e.id == self.id).for_update().first()
        return select(e for e in self.store if e.id == self.id).first()

    @db_session
    def query_key(self, key, for_update=False):
        elem = self._query_key(key, for_update=for_update)
        if elem:
            return StoreMeta(elem, store=self.store)


    def adjust_slice(self, elems, for_update=False):
        if for_update:
            elems = elems.for_update()
        begin, end = self.begin, self.end
        if begin and end:
            # pony doesn't support step here
            if begin < 0:
                begin = len(self) + begin
            if end < 0:
                end = len(self) + end
            if begin > end:
                begin, end = end, begin
            elems = elems[begin:end]
        elif begin:
            if begin < 0:
                begin = len(self) + begin
            elems = elems[begin:]
        elif end:
            if end < 0:
                end = len(self) + end
            elems = elems[:end]
        else:
            elems = elems[:]
        return elems

    @db_session
    def __len__(self):
        return count(e for e in self.store)