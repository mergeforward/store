import json
import os
import uuid
from copy import copy
from datetime import datetime
from pony.orm.ormtypes import TrackedValue
from pony.orm import (Database, Json, PrimaryKey, Required, commit, count,
                      db_session, delete, desc, select, raw_sql)

from store.parser import parse

SCHEMA_CHECK = os.getenv('SCHEMA_CHECK', True)

try:
    from cerberus import Validator
except Exception:
    pass

try:
    import jsonschema
except Exception:
    pass

def get_json_value(data, key):
    result = data
    keys = key.split('.')
    for k in keys:
        try:
            k = int(k)
        except:
            pass
        result = result.__getitem__(k)
    return result

def set_json_value(data, key, value):
    result = data
    keys = key.split('.')
    for k in keys[:-1]:
        try:
            k = int(k)
        except:
            pass
        result = result.__getitem__(k)
    result[keys[-1]] = value
    return data
    
def del_json_key(data, key):
    result = data
    keys = key.split('.')
    for k in keys[:-1]:
        try:
            k = int(k)
        except:
            pass
        result = result.__getitem__(k)
    del result[keys[-1]]
    return result

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

        return [elem.__getattribute__(key).get_untracked() for elem in self.elems]

    @db_session
    def __setattr__(self, key, data):
        if key in ['elems'] or key.startswith('_'):
            return super().__setattr__(key, data)
        for elem in self.elems:
            elem.__setattr__(key, data)

STORE_META_SAFE_ATTR = ['store', 'id', 'key', 'data', 'meta', 'create', 'update',
                   'update_meta', 'delete_meta',
                   'replace_data', 'replace_meta', 'replace_all',
                   'update_data_multi', 'update_meta_multi'
                   ]
class StoreMeta:

    def __init__(self, elem, store=None):
        self.store = store
        self.id = elem.id
        self.key = elem.key
        self.data = elem.data
        self.meta = elem.meta
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
    def __getattribute__(self, key):
        if key in STORE_META_SAFE_ATTR or key.startswith('_'):
            return object.__getattribute__(self, key)

        elem = select(e for e in self.store if e.id == self.id).first()
        if elem:
            if isinstance(elem.data, dict):
                return elem.data.get(key)
                
    @db_session
    def __setattr__(self, key, data):
        if key in STORE_META_SAFE_ATTR or key.startswith('_'):
            return super().__setattr__(key, data)
        elem = select(e for e in self.store if e.id == self.id).for_update().first()
        if elem is None:
            raise Exception('elem not found')
        else:
            if isinstance(elem.data, dict):
                elem.data[key] = data
                elem.update = datetime.utcnow()

                self.data = elem.data
                self.update = elem.update.strftime("%Y-%m-%dT%H:%M:%S")
            else:
                raise Exception('data not dict!')


    @db_session
    def __setitem__(self, key, data):
        elem = select(e for e in self.store if e.id == self.id).for_update().first()
        if elem is None:
            raise Exception('elem not found')
        else:
            if isinstance(elem.data, dict) :
                copied = copy(elem.data)
                set_json_value(copied, key, data)

                elem.data = copied
                elem.update = datetime.utcnow()

                self.data = elem.data
                self.update = elem.update.strftime("%Y-%m-%dT%H:%M:%S")
            else:
                raise Exception('data not dict!')

    @db_session
    def __getitem__(self, key):
        elem = select(e for e in self.store if e.id == self.id).first()
        if elem:
            return get_json_value(elem.data, key)

    @db_session
    def __delitem__(self, key):
        elem = select(e for e in self.store if e.id == self.id).for_update().first()
        if isinstance(elem.data, dict) :
            copied = copy(elem.data)
            new_data = del_json_key(copied, key)

            elem.data = new_data
            elem.update = datetime.utcnow()

            self.data = elem.data
            self.update = elem.update.strftime("%Y-%m-%dT%H:%M:%S")
        else:
            elem.meta = {}


    # similar to __setitem__
    @db_session(retry=3)
    def update_meta(self, key, meta):
        elem = select(e for e in self.store if e.id == self.id).for_update().first()
        if isinstance(elem.meta, dict) :
            copied = copy(elem.meta)
            set_json_value(copied, key, meta)

            elem.meta = copied
            elem.update = datetime.utcnow()

            self.meta = elem.meta
            self.update = elem.update.strftime("%Y-%m-%dT%H:%M:%S")
        else:
            elem.meta = {}

    # similar to __delitem__
    @db_session(retry=3)
    def delete_meta(self, key):
        elem = select(e for e in self.store if e.id == self.id).for_update().first()
        if isinstance(elem.meta, dict) :
            copied = copy(elem.meta)
            new_meta = del_json_key(copied, key)

            elem.meta = new_meta
            elem.update = datetime.utcnow()

            self.meta = elem.meta
            self.update = elem.update.strftime("%Y-%m-%dT%H:%M:%S")
        else:
            elem.meta = {}


    @db_session(retry=3)
    def replace_meta(self, meta):
        if isinstance(meta, dict):
            elem = select(e for e in self.store if e.id == self.id).for_update().first()
            elem.meta = meta
            elem.update = datetime.utcnow()
            self.meta = elem.meta
            self.update = elem.update.strftime("%Y-%m-%dT%H:%M:%S")

    @db_session(retry=3)
    def replace_data(self, data):
        if isinstance(data, dict):
            elem = select(e for e in self.store if e.id == self.id).for_update().first()
            elem.data = data
            elem.update = datetime.utcnow()
            self.data = elem.data
            self.update = elem.update.strftime("%Y-%m-%dT%H:%M:%S")

    @db_session(retry=3)
    def replace_all(self, data, meta):
        if isinstance(data, dict):
            elem = select(e for e in self.store if e.id == self.id).for_update().first()
            elem.data = data
            elem.meta = meta
            elem.update = datetime.utcnow()
            self.data = elem.data
            self.meta = elem.meta
            self.update = elem.update.strftime("%Y-%m-%dT%H:%M:%S")

    @db_session
    def update_data_multi(self, data):
        elem = select(e for e in self.store if e.id == self.id).for_update().first()
        if elem is None:
            raise Exception('elem not found')
        else:
            if isinstance(elem.data, dict) :
                copied = copy(elem.data)
                for key, value in data.items():
                    set_json_value(copied, key, value)

                elem.data = copied
                elem.update = datetime.utcnow()

                self.data = elem.data
                self.update = elem.update.strftime("%Y-%m-%dT%H:%M:%S")
            else:
                raise Exception('data not dict!')

    @db_session(retry=3)
    def update_meta_multi(self, meta):
        elem = select(e for e in self.store if e.id == self.id).for_update().first()
        if isinstance(elem.meta, dict) :
            copied = copy(elem.meta)
            for key, value in meta.items():
                set_json_value(copied, key, value)

            elem.meta = copied
            elem.update = datetime.utcnow()

            self.meta = elem.meta
            self.update = elem.update.strftime("%Y-%m-%dT%H:%M:%S")
        else:
            elem.meta = {}


class Store(object):
    _safe_attrs = ['store', 'database', 'tablename', 
                   'begin', 'end', 'order', 
                   'add', 'register_attr', 'slice', 'adjust_slice', 'provider',
                   'query_key', 'count', 'desc', 'asc',
                   'query_meta', 'update_meta', 'delete_meta',
                   'provider', 'user', 'password', 'host', 'port', 'database', 'filename',
                   'schema', 
                   'validate', 'model', 'meta',
                   'search'
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
                 schema = None, 
                 validate=None, version="meta", model=None,
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


    def validate(self, data, meta=None, extra=None):
        if SCHEMA_CHECK and meta:
            schema_version = meta.get("schema_version")
            schema_type = meta.get("schema_type")
            schema = self.schema.get(schema_version) 

            if isinstance(data, TrackedValue):
                data = data.get_untracked()
            if isinstance(schema, TrackedValue):
                schema = schema.get_untracked()



            if schema_type == 'cerberus':
                validator = Validator()
                r = validator.validate(data, schema)
                if not r:
                    if extra:
                        raise StoreException(f'{schema_type}:{schema_type} {validator.errors}, extra: {extra}')
                    raise StoreException(f'{schema_type}:{schema_type} {validator.errors}')
            elif schema_type == 'jsonschema':
                validator = jsonschema
                try:
                    validator.validate(data, schema)
                except jsonschema.exceptions.ValidationError as e:
                    if extra:
                        raise StoreException(f'{schema_type}:{schema_type} {e}, extra: {extra}')
                    raise StoreException(f'{schema_type}:{schema_type} {e}')
            else:
                raise StoreException(f'schema type invalid: {schema_type}')

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

    @db_session(retry=3)
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
            self.validate(elem.data, meta=elem.meta )
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
    def __getitem__(self, key, for_update=False):
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
            elems = elems.order_by(lambda o: (desc(o.update), desc(o.id)))
        else:
            elems = elems.order_by(lambda o: (o.update, o.id))
        elems = self.adjust_slice(elems, for_update=for_update)
        for elem in elems:
            self.validate(elem.data, meta=elem.meta, extra=elem.key )
        return StoreMetas(elems, store=self.store)


    @db_session(retry=3)
    def __setitem__(self, key, data):

        if isinstance(key, slice):
            raise StoreException('not implemented!')
        elif isinstance(key, tuple):
            key='.'.join(key)
        
        self.validate(data, meta=self.meta)

        if key.isidentifier():
            if key in Store._safe_attrs or key.startswith('_'):
                return super().__setattr__(key, data)

            item = select(e for e in self.store if e.key == key).first()
            if item is None:
                self.store(key=key, data=data, meta=self.meta)
            else:
                item.data = data
                item.update = datetime.utcnow()
            return 


        filters = parse(key)
        elems = select(e for e in self.store)
        if filters:
            elems = elems.filter(filters)
        if self.order_by == 'desc':
            elems = elems.order_by(lambda o: (desc(o.update), desc(o.id)))
        else:
            elems = elems.order_by(lambda o: (o.update, o.id))
        elems = self.adjust_slice(elems, for_update=True)
        if elems:
            now = datetime.utcnow()
            for elem in elems:
                elem.data = data
                elem.update = now
        else:
            # for key like 'Pod_xxx-xxx-xxx
            item = select(e for e in self.store if e.key == key).first()
            if item is None:
                self.store(key=key, data=data, meta=self.meta)
            else:
                item.data = data
                item.update = datetime.utcnow()


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
            elems = elems.order_by(lambda o: (desc(o.update), desc(o.id)))
        else:
            elems = elems.order_by(lambda o: (o.update, o.id))
        if elems:
            for elem in elems:
                # self.validate(elem.data, meta=elem.meta)
                elem.delete()
        return
       

    @db_session
    def __delattr__(self, key):
        delete(e for e in self.store if e.key == key)


    @db_session
    def add(self, data, key=None):
        self.validate(data, meta=self.meta)
        hex = uuid.uuid1().hex
        key = "STORE_{}".format(hex) if not isinstance(key, str) else key
        self.store(key=key, data=data, meta=self.meta)
        return key

    @db_session
    def query_key(self, key, for_update=False):
        elem = None
        if for_update:
            elem = select(e for e in self.store if e.key == key).for_update().first()
        else:
            elem = select(e for e in self.store if e.key == key).first()
        if elem:
            self.validate(elem.data, meta=elem.meta)
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
            elems = elems.order_by(lambda o: (desc(o.update), desc(o.id)))
        else:
            elems = elems.order_by(lambda o: (o.update, o.id))
        elems = self.adjust_slice(elems, for_update=for_update)
        for elem in elems:
            self.validate(elem.data, extra=elem.key, meta=elem.meta)
        return StoreMetas(elems, store=self.store)


    def adjust_slice(self, elems, for_update=False):
        if for_update:
            elems = elems.for_update()
        begin, end = self.begin, self.end

        length = len(self)
        if begin and end:
            # pony doesn't support step here
            if begin < 0:
                begin = length + begin
            if end < 0:
                end = length + end
            if begin > end:
                begin, end = end, begin
            elems = elems[begin:end]
        elif begin:
            if begin < 0:
                begin = length + begin
            elems = elems[begin:]
        elif end:
            if end < 0:
                end = length + end
            elems = elems[:end]
        else:
            elems = elems[:]
        return elems

    @db_session
    def __len__(self):
        return count(e for e in self.store)


    @db_session
    def search(self, condition, for_update=False, fuzzy=True):
        elems = select(e for e in self.store)
        if condition:
            for key, value in condition.items():
                if isinstance(value, str):
                    if fuzzy:
                        if self.provider == 'mysql':
                            sql = f'json_search(`e`.`data`, "all", "%%{value}%%", NULL, "$$.{key}")'

                            # elems = elems.filter(lambda e: raw_sql(sql))
                        else:
                            sql = f'jsonb_path_exists("e"."data", \'$$.{key} ? (@ like_regex "{value}" flag "i")\')'
                            # print(sql, '????')
                            elems = elems.filter(lambda e: raw_sql(sql))
                    else:
                        if self.provider == 'mysql':
                            sql = f'json_search(`e`.`data`, "all", "{value}", NULL, "$$.{key}")'
                            elems = elems.filter(lambda e: raw_sql(sql))
                        else:
                            sql = f'jsonb_path_exists("e"."data", \'$$.{key} ? (@ == "{value}")\')'
                            elems = elems.filter(lambda e: raw_sql(sql))
                    # lambda_filters.append(raw_sql(sql))
                else:
                    if isinstance(value, list):
                        if '.' in key:
                            keys = key.split('.')
                        else:
                            keys = [key]

                        if self.provider == 'mysql':
                            # elems = elems.filter(lambda e: e.data[key] in value)
                            for i,k in enumerate(keys):
                                if i == 0:
                                    sql = f'e.data["{k}"]'
                                else:
                                    sql += f'["{k}"]'
                            sql += f' in {value}'


                            elems = elems.filter(sql)
                        else:
                            sql = f'e.data'
                            for i,k in enumerate(keys):
                                if i == len(keys) - 1:
                                    sql += '->>'
                                else:
                                    sql += '->'
                                sql += f"'{k}'"

                            # only string supported
                            v = [f"'{e}'" for e in value]
                            value_str = ', '.join(v)
                            sql += f' in ({value_str})'

                            # elems = elems.filter(sql)
                            elems = elems.filter(lambda e: raw_sql(sql))
                        # lambda_filters.append(raw_sql(sql))
                    else:
                        
                        if self.provider == 'mysql':
                            # elems = elems.filter(lambda e: e.data[key] == value)
                            sql = f'json_extract(`e`.`data`, "$$.{key}") = {value}'
                            elems = elems.filter(lambda e: raw_sql(sql))
                        else:
                            sql = f'jsonb_path_exists("e"."data", \'$$.{key} ? (@ == {value})\')'
                            elems = elems.filter(lambda e: raw_sql(sql))

        if self.order == 'desc':
            elems = elems.order_by(lambda o: (desc(o.update), desc(o.id)))
        else:
            elems = elems.order_by(lambda o: (o.update, o.id))
        elems = self.adjust_slice(elems, for_update=for_update)
        for elem in elems:
            self.validate(elem.data, meta=elem.meta, extra=elem.key )
        return StoreMetas(elems, store=self.store)
    