import json
import os
import uuid
from copy import copy
from datetime import datetime

from pony.orm import (Database, Json, PrimaryKey, Required, commit, count,
                      db_session, delete, desc, select)
from store.parser import parse
try:
    from cerberus import Validator
    SCHEMA_CHECK = True
except Exception:
    SCHEMA_CHECK = False


class StoreException(Exception):
    pass

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
        return [elem[key] for elem in self.elems]

    @db_session
    def __setitem__(self, key, data):
        if isinstance(key, int):
            self.elems[key] = data
            return
        for elem in self.elems:
            elem[key] = data


    @db_session
    def __getattribute__(self, key):
        if key in ['elems'] or key.startswith('_'):
            return object.__getattribute__(self, key)

        return [elem.__getattribute__(key) for elem in self.elems]

    @db_session
    def __setattr__(self, key, data):
        if key in ['elems'] or key.startswith('_'):
            return super().__setattr__(key, data)
        for elem in self.elems:
            elem.__setattr__(key, data)


class StoreMeta:
    def __init__(self, elem, store=None):
        self.store = store
        self.id = elem.id
        self.key = elem.key
        self.data = elem.data
        self.create = elem.create.strftime("%Y-%m-%dT%H:%M:%S")
        self.update = elem.update.strftime("%Y-%m-%dT%H:%M:%S")

    def __str__(self):
        return "id: {}, key: {}, data: {}, create: {}, update: {}".format(self.id, self.key, self.data, self.create, self.update)

    @db_session
    def __assign__(self, data):
        elem = select(e for e in self.store if e.id == self.id).for_update().first()
        if elem is None:
            raise Exception('elem not found')
        else:
            elem.data = data
            elem.update = datetime.utcnow()

            self.data = elem.data
            self.update = elem.update.strftime("%Y-%m-%dT%H:%M:%S")

    @db_session
    def __setattr__(self, key, data):
        if key in ['store', 'id', 'key', 'data', 'create', 'update'] or key.startswith('_'):
            return super().__setattr__(key, data)
        elem = select(e for e in self.store if e.id == self.id).for_update().first()
        if elem is None:
            raise Exception('elem not found')
        else:
            if key == 'meta':
                elem.meta = data
                elem.update = datetime.utcnow()
            elif isinstance(elem.data, dict):
                elem.data[key] = data
                elem.update = datetime.utcnow()

                self.data = elem.data
                self.update = elem.update.strftime("%Y-%m-%dT%H:%M:%S")
            else:
                raise Exception('data not dict!')

    @db_session
    def __getattribute__(self, key):
        if key in ['store', 'id', 'key', 'data', 'create', 'update'] or key.startswith('_'):
            return object.__getattribute__(self, key)

        elem = select(e for e in self.store if e.id == self.id).first()
        if elem:
            if key=='meta':
                return elem.meta
            if isinstance(elem.data, dict):
                return elem.data.get(key)

    @db_session
    def __setitem__(self, key, data):
        elem = select(e for e in self.store if e.id == self.id).for_update().first()
        if elem is None:
            raise Exception('elem not found')
        else:
            if isinstance(elem.data, dict) or \
               (isinstance(key, int) and isinstance(elem.data, list)):
                elem.data[key] = data
                elem.update = datetime.utcnow()

                self.data = elem.data
                self.update = elem.update.strftime("%Y-%m-%dT%H:%M:%S")
            else:
                raise Exception('data not dict!')

    @db_session
    def __getitem__(self, key):
        elem = select(e for e in self.store if e.id == self.id).first()
        if elem:
            if isinstance(key, int):
                return elem.data[key]
            else:
                return elem.data.get(key)


class Store(object):
    _safe_attrs = ['store', 'database', 'tablename', 
                   'begin', 'end', 'order', 
                   'add', 'register_attr', 'slice', 'adjust_slice', 'provider',
                   'query_key', 'count', 'desc', 'asc',
                   'query_meta', 'update_meta', 'delete_meta',
                   'provider', 'user', 'password', 'host', 'port', 'database', 'filename',
                   'schema', 'validate', 'model', 'meta',
                   ]

    provider = 'sqlite'
    user = 'test'
    password = 'test'
    host = 'localhost'
    port = 5432
    database = 'test'
    filename = 'database.sqlite'
    order = 'desc'
    schema = None
    begin = None
    end = None
    model = None
    meta = {}
    

    def __init__(self,
                 provider=None, user=None, password=None,
                 host=None, port=None, database=None, filename=None,
                 begin=None, end=None, order=None,
                 schema = None, validate=None, version="meta", model=None,
                 meta = None
                 ):
        self.provider = provider or self.provider
        self.filename = filename or self.filename
        self.user = user or self.user
        self.password = password or self.password
        self.host = host or self.host
        self.port = port or self.port
        self.database = database or self.database
        self.schema = schema or self.schema
        self.begin = begin or self.begin
        self.end = end or self.end
        self.order = order or self.order
        self.model = model or self.model
        self.meta = meta or self.meta

        if self.provider == 'sqlite':
            if not self.filename.startswith('/'):
                self.filename = os.getcwd()+'/' + self.filename

            self.database = Database(
                provider=self.provider, 
                filename=self.filename, 
                create_db=True)
        elif self.provider == 'mysql':
            self.database = Database(
                provider=self.provider, 
                user=self.user, 
                password=self.password,
                host=self.host, 
                port=self.port, 
                database=self.database,
                charset="utf8mb4"
                )
        elif self.provider == 'postgres':
            self.database = Database(
                provider=self.provider, 
                user=self.user, 
                password=self.password,
                host=self.host, 
                port=self.port, 
                database=self.database,
                )
        else:
            raise StoreException(f'provider {provider} not supported')

        self.tablename = self.__class__.__name__

        if not self.model:
            self.model = dict(
                id=PrimaryKey(int, auto=True),
                create=Required(datetime, sql_default='CURRENT_TIMESTAMP', default=lambda: datetime.utcnow()),
                update=Required(datetime, sql_default='CURRENT_TIMESTAMP', default=lambda: datetime.utcnow()),
                key=Required(str, index=True, unique=True),
                data=Required(Json, volatile=True, default={}),
                meta=Required(Json, volatile=True, default={})
            )

        self.store = type(self.tablename, (self.database.Entity,), self.model)
        self.database.generate_mapping(create_tables=True, check_tables=True)


    def validate(self, data, extra=None, meta=None):
        if SCHEMA_CHECK and self.schema:
            validator = Validator()
            if meta:
                schema_version = meta.get("schema_version")
                if schema_version:
                    validator.schema = self.schema.get(schema_version)
                else:
                    validator.schema = self.schema
            else:
                validator.schema = self.schema
            r = validator.validate(data)
            if not r:
                if extra:
                    raise StoreException(f'{validator.errors}, extra: {extra}')
                raise StoreException(validator.errors)

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
    def __setattr__(self, key, data):
        if key in Store._safe_attrs or key.startswith('_'):
            return super().__setattr__(key, data)

        self.validate(data, meta=self.meta)
        item = select(e for e in self.store if e.key == key).first()
        if item is None:
            self.store(key=key, data=data, meta=self.meta)
        else:
            item.data = data
            item.update = datetime.utcnow()

    @db_session
    def __getattribute__(self, key):
        if key in Store._safe_attrs or key.startswith('_'):
            return object.__getattribute__(self, key)

        elem = select(e for e in self.store if e.key == key).first()
        if elem:
            self.validate(elem.data, meta=self.meta )
            return StoreMeta(elem, store=self.store)
        return None

    @db_session
    def count(self, key):
        if isinstance(key, slice):
            raise StoreException('not implemented!')
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
            raise StoreException('not implemented!')
        elif isinstance(key, tuple):
            key='.'.join(key)

        # string key
        filters = parse(key)
        elems = select(e for e in self.store)
        if filters:
            elems = elems.filter(filters)
        if self.order == 'desc':
            elems = elems.order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id))
        elems = self.adjust_slice(elems, for_update=False)
        for elem in elems:
            self.validate(elem.data, meta=elem.meta, extra=elem.key )
        return StoreMetas(elems, store=self.store)


    @db_session
    def __setitem__(self, key, data):

        if isinstance(key, slice):
            raise StoreException('not implemented!')
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
                elem.data = data
                elem.update = now
        else:
            if key.isidentifier():
                return self.__setattr__(key, data)
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
                self.validate(elem.data, meta=self.meta)
                elem.delete()
        return
       

    @db_session
    def __delattr__(self, key):
        delete(e for e in self.store if e.key == key)


    @db_session
    def add(self, data, key=None):
        self.validate(data, meta=self.meta)
        hex = uuid.uuid1().hex
        key = "_{}".format(hex) if not isinstance(key, str) else key
        self.store(key=key, data=data, meta=self.meta)
        return key

    @db_session
    def query_key(self, key, for_update=False):
        elem = None
        if for_update:
            elem = select(e for e in self.store if e.id == self.id).for_update().first()
        else:
            elem = select(e for e in self.store if e.id == self.id).first()
        if elem:
            self.validate(elem.data, meta=self.meta)
            return StoreMeta(elem, store=self.store)

    @db_session
    def query_meta(self, key, for_update=False):
        if isinstance(key, slice):
            raise StoreException('not implemented!')
        elif isinstance(key, tuple):
            key='.'.join(key)

        # string key
        filters = parse(key, "meta")
        elems = select(e for e in self.store)
        if filters:
            elems = elems.filter(filters)
        if self.order == 'desc':
            elems = elems.order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id))
        elems = self.adjust_slice(elems, for_update=for_update)
        for elem in elems:
            self.validate(elem.data, extra=elem.key, meta=self.meta)
        return StoreMetas(elems, store=self.store)

    @db_session
    def update_meta(self, cond, key, data):
        elems = self.__getitem__(key=cond)
        for elem in elems:
            elem.meta[key] = data

    @db_session
    def delete_meta(self, cond, key):
        elems = self.__getitem__(key=cond)
        for elem in elems:
            del elem.meta[key]

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