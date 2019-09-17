from pony.orm import Database, Required, PrimaryKey, Json, db_session, select, commit, desc, delete, count
from datetime import datetime
from copy import copy
import os
import uuid
import json


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
        elem = select(e for e in self.store if e.id == self.id).order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id)).for_update().first()
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
        elem = select(e for e in self.store if e.id == self.id).order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id)).for_update().first()
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

        elem = select(e for e in self.store if e.id == self.id).order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id)).first()
        if elem:
            if isinstance(elem.value, dict):
                return elem.value.get(key)

    @db_session
    def __setitem__(self, key, value):
        elem = select(e for e in self.store if e.id == self.id).order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id)).for_update().first()
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
        elem = select(e for e in self.store if e.id == self.id).order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id)).first()
        if elem:
            if isinstance(elem.value, dict) or \
               (isinstance(key, int) and isinstance(elem.value, list)) or \
               (isinstance(key, int) and isinstance(elem.value, str)):
                if isinstance(key, int):
                    return elem.value[key]
                else:
                    return elem.value.get(key)
            



class Store(object):
    _safe_attrs = ['store', 'database', 'tablename', 'begin',
                   'end', 'add', 'register_attr', 'slice', 'adjust_slice', 'provider',
                   'query_key', 'query_value', 
                   'provider', 'user', 'password', 'host', 'port', 'database', 'filename'
                   
                   ]

    provider = 'sqlite'
    user = 'test'
    password = 'test'
    host = 'localhost'
    port = 5432
    database = 'test'
    filename = 'database.sqlite'

    def __init__(self,
                 provider=None, user=None, password=None,
                 host=None, port=None, database=None, filename=None,
                 begin=None, end=None):
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

    @staticmethod
    def register_attr(name):
        if isinstance(name, str) and name not in Store._safe_attrs:
            Store._safe_attrs.append(name)

    @db_session
    def __setattr__(self, key, value):
        if key in Store._safe_attrs or key.startswith('_'):
            return super().__setattr__(key, value)
        item = select(e for e in self.store if e.key == key).order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id)).first()
        if item is None:
            self.store(key=key, value=value)
        else:
            item.value = value
            item.update = datetime.utcnow()

    @db_session
    def __getattribute__(self, key):
        if key in Store._safe_attrs or key.startswith('_'):
            return object.__getattribute__(self, key)

        elem = select(e for e in self.store if e.key == key).order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id)).first()
        if elem:
            return StoreMeta(elem, store=self.store)
        return None

    @db_session
    def __setitem__(self, key, value):

        if isinstance(key, slice):
            raise Exception('not implemented!')
        elif isinstance(key, tuple):
            if len(key) > 4:
                raise Exception('not implemented!')
            elems = self._query_value(*key)
            if elems:
                now = datetime.utcnow()
                for elem in elems:
                    elem.value = value
                    elem.update = now
            else:
                raise Exception('not implemented')
            return
        elif isinstance(key, str):
            
            if ',' in key:
                keys = key.split(',')
                if len(keys) > 0:
                    keys = [k for k in keys if len(k)>0]
                elems = self._query_value(*keys, for_update=True)
                if elems:
                    now = datetime.utcnow()
                    for elem in elems:
                        elem.value = value
                        elem.update = now
                else:
                    raise Exception('not implemented')
                return

            elif '=' in key or '>' in key or '<' in key or ':' in key:
                elems = self.query_value(key, for_update=True)
                if elems:
                    now = datetime.utcnow()
                    for elem in elems:
                        elem.value = value
                        elem.update = now
                else:
                    raise Exception('not implemented')
                return

            elif key == '*':
                elems = select(e for e in self.store).order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id))
                elems = self.adjust_slice(elems, for_update=True)

                if elems:
                    now = datetime.utcnow()
                    for elem in elems:
                        elem.value = value
                        elem.update = now
                else:
                    self.store(key=key, value=value)
                return

            
            if '||' in key:
                keys_sp = [k for k in key.split('||') if len(k)>0]
                if len(keys_sp) >1:
                    elems = select(e for e in self.store if e.key in keys_sp).order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id))
                    elems = self.adjust_slice(elems, for_update=True)
                    if elems:
                        now = datetime.utcnow()
                        for elem in elems:
                            elem.value = value
                            elem.update = now
                    else:
                        self.store(key=key, value=value)
                    return

            if key[0] == '(' and key[-1] == ')':
                elems = select(e for e in self.store if key[1:-1] in e.key).order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id))
                elems = self.adjust_slice(elems, for_update=True)
                if elems:
                    now = datetime.utcnow()
                    for elem in elems:
                        elem.value = value
                        elem.update = now
                else:
                    self.store(key=key, value=value)
                return
            elif key[0] == ')' and key[-1] == '(':
                elems = select(e for e in self.store if key[1:-1] not in e.key).order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id))
                elems = self.adjust_slice(elems, for_update=True)
                if elems:
                    now = datetime.utcnow()
                    for elem in elems:
                        elem.value = value
                        elem.update = now
                else:
                    self.store(key=key, value=value)
                return
            elif key[0] == '^' and key[-1] == '$':
                elems = select(e for e in self.store if e.key == key[1:-1]).order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id))
                elems = self.adjust_slice(elems, for_update=True)
                if elems:
                    now = datetime.utcnow()
                    for elem in elems:
                        elem.value = value
                        elem.update = now
                else:
                    self.store(key=key, value=value)
                return
            elif key[0] == '^' and key[-1] != '$':
                elems = select(e for e in self.store if e.key.startswith(key[1:])).order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id))
                elems = self.adjust_slice(elems, for_update=True)
                if elems:
                    now = datetime.utcnow()
                    for elem in elems:
                        elem.value = value
                        elem.update = now
                else:
                    self.store(key=key, value=value)
                return
            elif key[0] != '^' and key[-1] == '$':
                elems = select(e for e in self.store if e.key.endswith(key[:-1])).order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id))
                elems = self.adjust_slice(elems, for_update=True)
                if elems:
                    now = datetime.utcnow()
                    for elem in elems:
                        elem.value = value
                        elem.update = now
                else:
                    self.store(key=key, value=value)
                return
            else:
                elem = select(e for e in self.store if e.key == key).order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id)).for_update().first()
                if elem:
                    elem.value = value
                    elem.update = datetime.utcnow()
                else:
                    self.store(key=key, value=value)
            return
        raise Exception('not implemented!')

    @db_session
    def __getitem__(self, key):
        if isinstance(key, slice):
            raise Exception('not implemented!')
        elif isinstance(key, tuple):
            if len(key) > 4:
                raise Exception('not implemented!')
            return self.query_value(*key)
        elif isinstance(key, str):
            if ',' in key:
                keys = key.split(',')
                if len(keys) > 0:
                    keys = [k for k in keys if len(k)>0]
                return self.query_value(*keys)

            if '=' in key or '>' in key or '<' in key or ':' in key:
                return self.query_value(key)
            
            if key == '*':
                elems = select(e for e in self.store).order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id))
                elems = self.adjust_slice(elems)
                return StoreMetas(elems, store=self.store)

            if '||' in key:
                keys_sp = [k for k in key.split('||') if len(k)>0]
                if len(keys_sp) >1:
                    elems = select(e for e in self.store if e.key in keys_sp).order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id))
                    elems = self.adjust_slice(elems)
                    return StoreMetas(elems, store=self.store)

            if key[0] == '(' and key[-1] == ')':
                elems = select(e for e in self.store if key[1:-1] in e.key).order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id))
                return StoreMetas(elems, store=self.store)
            elif key[0] == ')' and key[-1] == '(':
                elems = select(e for e in self.store if key[1:-1] not in e.key).order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id))
                return StoreMetas(elems, store=self.store)
            elif key[0] == '^' and key[-1] == '$':
                elems = select(e for e in self.store if e.key == key[1:-1]).order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id))
                elems = self.adjust_slice(elems)
                return StoreMetas(elems, store=self.store)
            elif key[0] == '^' and key[-1] != '$':
                elems = select(e for e in self.store if e.key.startswith(key[1:])).order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id))
                elems = self.adjust_slice(elems)
                return StoreMetas(elems, store=self.store)
            elif key[0] != '^' and key[-1] == '$':
                elems = select(e for e in self.store if e.key.endswith(key[:-1])).order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id))
                elems = self.adjust_slice(elems)
                return StoreMetas(elems, store=self.store)
            else:
                elem = select(e for e in self.store if e.key == key).order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id)).first()
                if elem:
                    return StoreMeta(elem, store=self.store)

    @db_session
    def __delitem__(self, key):
        if isinstance(key, slice):
            raise Exception('not implemented!')
        elif isinstance(key, tuple):
            if len(key) > 4:
                raise Exception('not implemented!')
            elems = self._query_value(*key)
            if elems:
                for elem in elems:
                    elem.delete()
            return
        elif isinstance(key, str):
            
            if ',' in key:
                keys = key.split(',')
                if len(keys) > 0:
                    keys = [k for k in keys if len(k)>0]
                elems = self._query_value(*keys, for_update=True)
                if elems:
                    for elem in elems:
                        elem.delete()
                return

            elif '=' in key or '>' in key or '<' in key or ':' in key:
                elems = self._query_value(key, for_update=True)
                if elems:
                    for elem in elems:
                        elem.delete()
                return

            elif key == '*':
                elems = select(e for e in self.store).order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id))
                elems = self.adjust_slice(elems, for_update=True)

                if elems:
                    for elem in elems:
                        elem.delete()
                return


            if '||' in key:
                keys_sp = [k for k in key.split('||') if len(k)>0]
                if len(keys_sp) >1:
                    elems = select(e for e in self.store if e.key in keys_sp).order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id))
                    elems = self.adjust_slice(elems, for_update=True)
                    if elems:
                        for elem in elems:
                            elem.delete()
                    return

            if key[0] == '(' and key[-1] == ')':
                elems = select(e for e in self.store if key[1:-1] in e.key).order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id))
                elems = self.adjust_slice(elems, for_update=True)
                if elems:
                    for elem in elems:
                        elem.delete()
                return
            elif key[0] == ')' and key[-1] == '(':
                elems = select(e for e in self.store if key[1:-1] not in e.key).order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id))
                elems = self.adjust_slice(elems, for_update=True)
                if elems:
                    for elem in elems:
                        elem.delete()
                return
            elif key[0] == '^' and key[-1] == '$':
                elems = select(e for e in self.store if e.key == key[1:-1]).order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id))
                elems = self.adjust_slice(elems, for_update=True)
                if elems:
                    for elem in elems:
                        elem.delete()
                return
            elif key[0] == '^' and key[-1] != '$':
                elems = select(e for e in self.store if e.key.startswith(key[1:])).order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id))
                elems = self.adjust_slice(elems, for_update=True)
                if elems:
                    for elem in elems:
                        elem.delete()
                return
            elif key[0] != '^' and key[-1] == '$':
                elems = select(e for e in self.store if e.key.endswith(key[:-1])).order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id))
                elems = self.adjust_slice(elems, for_update=True)
                if elems:
                    for elem in elems:
                        elem.delete()
                return
            else:
                elem = select(e for e in self.store if e.key == key).order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id)).for_updaet().first()
                if elem:
                    elem.delete()
                    return 
        raise Exception('not implemented!')

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
            return select(e for e in self.store if e.id == self.id).order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id)).for_update().first()
        return select(e for e in self.store if e.id == self.id).order_by(lambda o: desc(o.create)).order_by(lambda o: desc(o.id)).first()

    @db_session
    def query_key(self, key, for_update=False):
        elem = self._query_key(key, for_update=for_update)
        if elem:
            return StoreMeta(elem, store=self.store)

    # ugly implementation
    @db_session
    def _query_value(self, *keys, for_update=False):
        try:
            lenkeys = len(keys)
            if lenkeys == 1:
                elems = self._query_elems0(*keys)
            elif lenkeys == 2:
                elems = self._query_elems1(*keys)
            elif lenkeys == 3:
                elems = self._query_elems2(*keys)
            elif lenkeys == 4:
                elems = self._query_elems3(*keys)
            else:
                raise Exception('not implemented!')

            if elems:
                elems = self.adjust_slice(elems, for_update=for_update)
                if elems:
                    return elems
        except TypeError:
            raise Exception('key invalid!')
        # return []
        return None

    def _query_elems0(self, *keys):
        if '&&' in keys[0]:
            part0, part1 = keys[0].split('&&', 1)
            if '>=' in part0:
                key0, value0 = part0.split('>=', 1)
                filter1 = lambda e: e.value[key0] >= float(value0)
            elif '<=' in part0:
                key0, value0 = part0.split('<=', 1)
                filter1 = lambda e: e.value[key0] <= float(value0)
            elif '!=' in part0:
                key0, value0 = part0.split('!=', 1)
                filter1 = lambda e: e.value[key0]  != value0
            elif '=' in part0:
                key0, value0 = part0.split('=', 1)
                filter1 = lambda e: e.value[key0]  == value0
            elif '>' in part0:
                key0, value0 = part0.split('>', 1)
                filter1 = lambda e: e.value[key0]  > float(value0)
            elif '=' in part0:
                key0, value0 = part0.split('<', 1)
                filter1 = lambda e: e.value[key0]  < float(value0)
            elif ':' in part0:
                key0, value0 = part0.split(':', 1)
                filter1 = lambda e: value0 in e.value[key0]
            else:
                filter1 = lambda e: e.value[part0] != None


            if '>=' in part1:
                key1, value1 = part1.split('>=', 1)
                filter2 = lambda e: e.value[key1]  >= float(value1)
            elif '<=' in part1:
                key1, value1 = part1.split('<=', 1)
                filter2 = lambda e: e.value[key1]  <= float(value1)
            elif '!=' in part1:
                key1, value1 = part1.split('!=', 1)
                filter2 = lambda e: e.value[key1]  != value1
            elif '=' in part1:
                key1, value1 = part1.split('=', 1)
                filter2 = lambda e: e.value[key1]  == value1
            elif '>' in part1:
                key1, value1 = part1.split('>', 1)
                filter2 = lambda e: e.value[key1]  > float(value1)
            elif '<' in part1:
                key1, value1 = part1.split('<', 1)
                filter2 = lambda e: e.value[key1]  < float(value1)
            elif ':' in part1:
                key1, value1 = part1.split(':', 1)
                filter2 = lambda e: value1 in e.value[key1] 
            else:
                filter2 = lambda e: e.value[part1] != None

            elems = select(e for e in self.store).filter(filter1).filter(filter2)

        elif '||' in keys[0]:
            # dum codes for or
            part0, part1 = keys[0].split('||', 1)
            if '>=' in part0 and '>=' in part1:
                key0, value0 = part0.split('>=', 1)
                key1, value1 = part1.split('>=', 1)
                filter0 = lambda e: e.value[key0]  >= value0 or e.value[key1] >= value1
            elif '>=' in part0 and '<=' in part1:
                key0, value0 = part0.split('>=', 1)
                key1, value1 = part1.split('<=', 1)
                filter0 = lambda e: e.value[key0]  >= value0 or e.value[key1] <= value1
            elif '>=' in part0 and '!=' in part1:
                key0, value0 = part0.split('>=', 1)
                key1, value1 = part1.split('!=', 1)
                filter0 = lambda e: e.value[key0]  >= value0 or e.value[key1] != value1
            elif '>=' in part0 and '=' in part1:
                key0, value0 = part0.split('>=', 1)
                key1, value1 = part1.split('=', 1)
                filter0 = lambda e: e.value[key0]  >= value0 or e.value[key1] == value1
            elif '>=' in part0 and '>' in part1:
                key0, value0 = part0.split('>=', 1)
                key1, value1 = part1.split('>', 1)
                filter0 = lambda e: e.value[key0]  >= value0 or e.value[key1] > value1
            elif '>=' in part0 and '<' in part1:
                key0, value0 = part0.split('>=', 1)
                key1, value1 = part1.split('<', 1)
                filter0 = lambda e: e.value[key0]  >= value0 or e.value[key1] < value1
            elif '>=' in part0 and ':' in part1:
                key0, value0 = part0.split('>=', 1)
                key1, value1 = part1.split(':', 1)
                filter0 = lambda e: e.value[key0]  >= value0 or value1 in e.value[key1]
            elif '>=' in part0 and '=' not in part1:
                key0, value0 = part0.split('>=', 1)
                filter0 = lambda e: e.value[key0] >= value0 or e.value[part1] != None


            elif '<=' in part0 and '>=' in part1:
                key0, value0 = part0.split('<=', 1)
                key1, value1 = part1.split('>=', 1)
                filter0 = lambda e: e.value[key0]  <= value0 or e.value[key1] >= value1
            elif '<=' in part0 and '<=' in part1:
                key0, value0 = part0.split('<=', 1)
                key1, value1 = part1.split('<=', 1)
                filter0 = lambda e: e.value[key0]  <= value0 or e.value[key1] <= value1
            elif '<=' in part0 and '!=' in part1:
                key0, value0 = part0.split('<=', 1)
                key1, value1 = part1.split('!=', 1)
                filter0 = lambda e: e.value[key0]  <= value0 or e.value[key1] != value1
            elif '<=' in part0 and '=' in part1:
                key0, value0 = part0.split('<=', 1)
                key1, value1 = part1.split('=', 1)
                filter0 = lambda e: e.value[key0]  <= value0 or e.value[key1] == value1
            elif '<=' in part0 and '>' in part1:
                key0, value0 = part0.split('<=', 1)
                key1, value1 = part1.split('>', 1)
                filter0 = lambda e: e.value[key0]  <= value0 or e.value[key1] > value1
            elif '<=' in part0 and '<' in part1:
                key0, value0 = part0.split('<=', 1)
                key1, value1 = part1.split('<', 1)
                filter0 = lambda e: e.value[key0]  <= value0 or e.value[key1] < value1
            elif '<=' in part0 and ':' in part1:
                key0, value0 = part0.split('<=', 1)
                key1, value1 = part1.split(':', 1)
                filter0 = lambda e: e.value[key0]  <= value0 or value1 in e.value[key1]
            elif '<=' in part0 and '=' not in part1:
                key0, value0 = part0.split('<=', 1)
                filter0 = lambda e: e.value[key0] <= value0 or e.value[part1] != None



            elif '!=' in part0 and '>=' in part1:
                key0, value0 = part0.split('!=', 1)
                key1, value1 = part1.split('>=', 1)
                filter0 = lambda e: e.value[key0]  != value0 or e.value[key1] >= value1
            elif '!=' in part0 and '<=' in part1:
                key0, value0 = part0.split('!=', 1)
                key1, value1 = part1.split('<=', 1)
                filter0 = lambda e: e.value[key0]  != value0 or e.value[key1] <= value1
            elif '!=' in part0 and '!=' in part1:
                key0, value0 = part0.split('!=', 1)
                key1, value1 = part1.split('!=', 1)
                filter0 = lambda e: e.value[key0]  != value0 or e.value[key1] != value1
            elif '!=' in part0 and '=' in part1:
                key0, value0 = part0.split('!=', 1)
                key1, value1 = part1.split('=', 1)
                filter0 = lambda e: e.value[key0]  != value0 or e.value[key1] == value1
            elif '!=' in part0 and '>' in part1:
                key0, value0 = part0.split('!=', 1)
                key1, value1 = part1.split('>', 1)
                filter0 = lambda e: e.value[key0]  != value0 or e.value[key1] > value1
            elif '!=' in part0 and '<' in part1:
                key0, value0 = part0.split('!=', 1)
                key1, value1 = part1.split('<', 1)
                filter0 = lambda e: e.value[key0]  != value0 or e.value[key1] < value1
            elif '!=' in part0 and ':' in part1:
                key0, value0 = part0.split('!=', 1)
                key1, value1 = part1.split(':', 1)
                filter0 = lambda e: e.value[key0]  != value0 or value1 in e.value[key1]
            elif '!=' in part0 and '=' not in part1:
                key0, value0 = part0.split('!=', 1)
                filter0 = lambda e: e.value[key0] != value0 or e.value[part1] != None

            elif '=' in part0 and '>=' in part1:
                key0, value0 = part0.split('=', 1)
                key1, value1 = part1.split('>=', 1)
                filter0 = lambda e: e.value[key0]  == value0 or e.value[key1] >= value1
            elif '=' in part0 and '<=' in part1:
                key0, value0 = part0.split('=', 1)
                key1, value1 = part1.split('<=', 1)
                filter0 = lambda e: e.value[key0]  == value0 or e.value[key1] <= value1
            elif '=' in part0 and '!=' in part1:
                key0, value0 = part0.split('=', 1)
                key1, value1 = part1.split('!=', 1)
                filter0 = lambda e: e.value[key0]  == value0 or e.value[key1] != value1
            elif '=' in part0 and '=' in part1:
                key0, value0 = part0.split('=', 1)
                key1, value1 = part1.split('=', 1)
                filter0 = lambda e: e.value[key0]  == value0 or e.value[key1] == value1
            elif '=' in part0 and '>' in part1:
                key0, value0 = part0.split('=', 1)
                key1, value1 = part1.split('>', 1)
                filter0 = lambda e: e.value[key0]  == value0 or e.value[key1] > value1
            elif '=' in part0 and '<' in part1:
                key0, value0 = part0.split('=', 1)
                key1, value1 = part1.split('<', 1)
                filter0 = lambda e: e.value[key0]  == value0 or e.value[key1] < value1
            elif '=' in part0 and ':' in part1:
                key0, value0 = part0.split('=', 1)
                key1, value1 = part1.split(':', 1)
                filter0 = lambda e: e.value[key0]  == value0 or value1 in e.value[key1]
            elif '=' in part0 and '=' not in part1:
                key0, value0 = part0.split('=', 1)
                filter0 = lambda e: e.value[key0] == value0 or e.value[part1] != None

            elif '>' in part0 and '>=' in part1:
                key0, value0 = part0.split('>', 1)
                key1, value1 = part1.split('>=', 1)
                filter0 = lambda e: e.value[key0]  > value0 or e.value[key1] >= value1
            elif '>' in part0 and '<=' in part1:
                key0, value0 = part0.split('>', 1)
                key1, value1 = part1.split('<=', 1)
                filter0 = lambda e: e.value[key0]  > value0 or e.value[key1] <= value1
            elif '>' in part0 and '!=' in part1:
                key0, value0 = part0.split('>', 1)
                key1, value1 = part1.split('!=', 1)
                filter0 = lambda e: e.value[key0] > value0 or e.value[key1] != value1
            elif '>' in part0 and '=' in part1:
                key0, value0 = part0.split('>', 1)
                key1, value1 = part1.split('=', 1)
                filter0 = lambda e: e.value[key0] > value0 or e.value[key1] == value1
            elif '>' in part0 and '>' in part1:
                key0, value0 = part0.split('>', 1)
                key1, value1 = part1.split('>', 1)
                filter0 = lambda e: e.value[key0] > value0 or e.value[key1] > value1
            elif '>' in part0 and '<' in part1:
                key0, value0 = part0.split('>', 1)
                key1, value1 = part1.split('<', 1)
                filter0 = lambda e: e.value[key0] > value0 or e.value[key1] < value1
            elif '>' in part0 and ':' in part1:
                key0, value0 = part0.split('>', 1)
                key1, value1 = part1.split(':', 1)
                filter0 = lambda e: e.value[key0] > value0 or value1 in e.value[key1]
            elif '>' in part0 and '=' not in part1:
                key0, value0 = part0.split('>', 1)
                filter0 = lambda e: e.value[key0] > value0 or e.value[part1] != None

            elif '<' in part0 and '>=' in part1:
                key0, value0 = part0.split('<', 1)
                key1, value1 = part1.split('>=', 1)
                filter0 = lambda e: e.value[key0]  < value0 or e.value[key1] >= value1
            elif '<' in part0 and '<=' in part1:
                key0, value0 = part0.split('<', 1)
                key1, value1 = part1.split('<=', 1)
                filter0 = lambda e: e.value[key0]  < value0 or e.value[key1] <= value1
            elif '<' in part0 and '!=' in part1:
                key0, value0 = part0.split('<', 1)
                key1, value1 = part1.split('!=', 1)
                filter0 = lambda e: e.value[key0] < value0 or e.value[key1] != value1
            elif '<' in part0 and '=' in part1:
                key0, value0 = part0.split('<', 1)
                key1, value1 = part1.split('=', 1)
                filter0 = lambda e: e.value[key0] < value0 or e.value[key1] == value1
            elif '<' in part0 and '>' in part1:
                key0, value0 = part0.split('<', 1)
                key1, value1 = part1.split('>', 1)
                filter0 = lambda e: e.value[key0] < value0 or e.value[key1] > value1
            elif '<' in part0 and '<' in part1:
                key0, value0 = part0.split('<', 1)
                key1, value1 = part1.split('<', 1)
                filter0 = lambda e: e.value[key0] < value0 or e.value[key1] < value1
            elif '<' in part0 and ':' in part1:
                key0, value0 = part0.split('<', 1)
                key1, value1 = part1.split(':', 1)
                filter0 = lambda e: e.value[key0] < value0 or value1 in e.value[key1]
            elif '<' in part0 and '=' not in part1:
                key0, value0 = part0.split('<', 1)
                filter0 = lambda e: e.value[key0] < value0 or e.value[part1] != None

            elif ':' in part0 and '>=' in part1:
                key0, value0 = part0.split(':', 1)
                key1, value1 = part1.split('>=', 1)
                filter0 = lambda e: value0 in e.value[key0] or e.value[key1] >= value1
            elif ':' in part0 and '<=' in part1:
                key0, value0 = part0.split('<', 1)
                key1, value1 = part1.split('<=', 1)
                filter0 = lambda e: value0 in e.value[key0] or e.value[key1] <= value1
            elif ':' in part0 and '!=' in part1:
                key0, value0 = part0.split('<', 1)
                key1, value1 = part1.split('!=', 1)
                filter0 = lambda e: value0 in e.value[key0] or e.value[key1] != value1
            elif ':' in part0 and '=' in part1:
                key0, value0 = part0.split('<', 1)
                key1, value1 = part1.split('=', 1)
                filter0 = lambda e: value0 in e.value[key0] or e.value[key1] == value1
            elif ':' in part0 and '>' in part1:
                key0, value0 = part0.split('<', 1)
                key1, value1 = part1.split('>', 1)
                filter0 = lambda e: value0 in e.value[key0] or e.value[key1] > value1
            elif ':' in part0 and '<' in part1:
                key0, value0 = part0.split('<', 1)
                key1, value1 = part1.split('<', 1)
                filter0 = lambda e: value0 in e.value[key0] or e.value[key1] < value1
            elif ':' in part0 and ':' in part1:
                key0, value0 = part0.split('<', 1)
                key1, value1 = part1.split(':', 1)
                filter0 = lambda e: value0 in e.value[key0] or value1 in e.value[key1]
            elif ':' in part0 and '=' not in part1:
                key0, value0 = part0.split(':', 1)
                filter0 = lambda e: value0 in e.value[key0] or e.value[part1] != None
            else:
                raise Exception('not implemented!')

            elems = select(e for e in self.store).filter(filter0)
        else:
            if '>=' in keys[0]:
                key, value = keys[0].split('>=', 1)
                elems = select(e for e in self.store if e.value[key] >= float(value))
            elif '<=' in keys[0]:
                key, value = keys[0].split('<=', 1)
                elems = select(e for e in self.store if e.value[key] <= float(value))
            elif '!=' in keys[0]:
                key, value = keys[0].split('!=', 1)
                elems = select(e for e in self.store).filter(lambda e: e.value[key] != value) 
            elif '=' in keys[0]:
                key, value = keys[0].split('=', 1)
                elems = select(e for e in self.store).filter(lambda e: e.value[key] == value) 
            elif '>' in keys[0]:
                key, value = keys[0].split('>', 1)
                elems = select(e for e in self.store if e.value[key] > float(value))
            elif '<' in keys[0]:
                key, value = keys[0].split('<', 1)
                elems = select(e for e in self.store if e.value[key] < float(value))
            elif ':' in keys[0]:
                key, value = keys[0].split(':', 1)
                elems = select(e for e in self.store if value in e.value[key])
            else:
                if self.provider == 'mysql':
                    elems = select(e for e in self.store if e.value[keys[0]] != None)
                else:
                    elems = select(e for e in self.store if keys[0] in e.value )
        return elems

    def _query_elems1(self, *keys):
        if '&&' in keys[1]:
            part0, part1 = keys[1].split('&&', 1)
            if '>=' in part0:
                key0, value0 = part0.split('>=', 1)
                filter1 = lambda e: e.value[keys[0]][key0] >= float(value0)
            elif '<=' in part0:
                key0, value0 = part0.split('<=', 1)
                filter1 = lambda e: e.value[keys[0]][key0] <= float(value0)
            elif '!=' in part0:
                key0, value0 = part0.split('!=', 1)
                filter1 = lambda e: e.value[keys[0]][key0]  != value0
            elif '=' in part0:
                key0, value0 = part0.split('=', 1)
                filter1 = lambda e: e.value[keys[0]][key0]  == value0
            elif '>' in part0:
                key0, value0 = part0.split('>', 1)
                filter1 = lambda e: e.value[keys[0]][key0]  > float(value0)
            elif '=' in part0:
                key0, value0 = part0.split('<', 1)
                filter1 = lambda e: e.value[keys[0]][key0]  < float(value0)
            elif ':' in part0:
                key0, value0 = part0.split(':', 1)
                filter1 = lambda e: value0 in e.value[keys[0]][key0]
            else:
                filter1 = lambda e: e.value[keys[0]][part0] != None


            if '>=' in part1:
                key1, value1 = part1.split('>=', 1)
                filter2 = lambda e: e.value[keys[0]][key1]  >= float(value1)
            elif '<=' in part1:
                key1, value1 = part1.split('<=', 1)
                filter2 = lambda e: e.value[keys[0]][key1]  <= float(value1)
            elif '!=' in part1:
                key1, value1 = part1.split('!=', 1)
                filter2 = lambda e: e.value[keys[0]][key1]  != value1
            elif '=' in part1:
                key1, value1 = part1.split('=', 1)
                filter2 = lambda e: e.value[keys[0]][key1]  == value1
            elif '>' in part1:
                key1, value1 = part1.split('>', 1)
                filter2 = lambda e: e.value[keys[0]][key1]  > float(value1)
            elif '<' in part1:
                key1, value1 = part1.split('<', 1)
                filter2 = lambda e: e.value[keys[0]][key1]  < float(value1)
            elif ':' in part1:
                key1, value1 = part1.split(':', 1)
                filter2 = lambda e: value1 in e.value[keys[0]][key1] 
            else:
                filter2 = lambda e: e.value[keys[0]][part1] != None

            elems = select(e for e in self.store).filter(filter1).filter(filter2)

        elif '||' in keys[1]:


            part0, part1 = keys[1].split('||', 1)
            if '>=' in part0 and '>=' in part1:
                key0, value0 = part0.split('>=', 1)
                key1, value1 = part1.split('>=', 1)
                filter0 = lambda e: e.value[keys[0]][key0]  >= value0 or e.value[keys[0]][key1] >= value1
            elif '>=' in part0 and '<=' in part1:
                key0, value0 = part0.split('>=', 1)
                key1, value1 = part1.split('<=', 1)
                filter0 = lambda e: e.value[keys[0]][key0]  >= value0 or e.value[keys[0]][key1] <= value1
            elif '>=' in part0 and '!=' in part1:
                key0, value0 = part0.split('>=', 1)
                key1, value1 = part1.split('!=', 1)
                filter0 = lambda e: e.value[keys[0]][key0]  >= value0 or e.value[keys[0]][key1] != value1
            elif '>=' in part0 and '=' in part1:
                key0, value0 = part0.split('>=', 1)
                key1, value1 = part1.split('=', 1)
                filter0 = lambda e: e.value[keys[0]][key0]  >= value0 or e.value[keys[0]][key1] == value1
            elif '>=' in part0 and '>' in part1:
                key0, value0 = part0.split('>=', 1)
                key1, value1 = part1.split('>', 1)
                filter0 = lambda e: e.value[keys[0]][key0]  >= value0 or e.value[keys[0]][key1] > value1
            elif '>=' in part0 and '<' in part1:
                key0, value0 = part0.split('>=', 1)
                key1, value1 = part1.split('<', 1)
                filter0 = lambda e: e.value[keys[0]][key0]  >= value0 or e.value[keys[0]][key1] < value1
            elif '>=' in part0 and ':' in part1:
                key0, value0 = part0.split('>=', 1)
                key1, value1 = part1.split(':', 1)
                filter0 = lambda e: e.value[keys[0]][key0]  >= value0 or value1 in e.value[keys[0]][key1]
            elif '>=' in part0 and '=' not in part1:
                key0, value0 = part0.split('>=', 1)
                filter0 = lambda e: e.value[keys[0]][key0] >= value0 or e.value[keys[0]][part1] != None


            elif '<=' in part0 and '>=' in part1:
                key0, value0 = part0.split('<=', 1)
                key1, value1 = part1.split('>=', 1)
                filter0 = lambda e: e.value[keys[0]][key0]  <= value0 or e.value[keys[0]][key1] >= value1
            elif '<=' in part0 and '<=' in part1:
                key0, value0 = part0.split('<=', 1)
                key1, value1 = part1.split('<=', 1)
                filter0 = lambda e: e.value[keys[0]][key0]  <= value0 or e.value[keys[0]][key1] <= value1
            elif '<=' in part0 and '!=' in part1:
                key0, value0 = part0.split('<=', 1)
                key1, value1 = part1.split('!=', 1)
                filter0 = lambda e: e.value[keys[0]][key0]  <= value0 or e.value[keys[0]][key1] != value1
            elif '<=' in part0 and '=' in part1:
                key0, value0 = part0.split('<=', 1)
                key1, value1 = part1.split('=', 1)
                filter0 = lambda e: e.value[keys[0]][key0]  <= value0 or e.value[keys[0]][key1] == value1
            elif '<=' in part0 and '>' in part1:
                key0, value0 = part0.split('<=', 1)
                key1, value1 = part1.split('>', 1)
                filter0 = lambda e: e.value[keys[0]][key0]  <= value0 or e.value[keys[0]][key1] > value1
            elif '<=' in part0 and '<' in part1:
                key0, value0 = part0.split('<=', 1)
                key1, value1 = part1.split('<', 1)
                filter0 = lambda e: e.value[keys[0]][key0]  <= value0 or e.value[keys[0]][key1] < value1
            elif '<=' in part0 and ':' in part1:
                key0, value0 = part0.split('<=', 1)
                key1, value1 = part1.split(':', 1)
                filter0 = lambda e: e.value[keys[0]][key0]  <= value0 or value1 in e.value[keys[0]][key1]
            elif '<=' in part0 and '=' not in part1:
                key0, value0 = part0.split('<=', 1)
                filter0 = lambda e: e.value[keys[0]][key0] <= value0 or e.value[keys[0]][part1] != None



            elif '!=' in part0 and '>=' in part1:
                key0, value0 = part0.split('!=', 1)
                key1, value1 = part1.split('>=', 1)
                filter0 = lambda e: e.value[keys[0]][key0]  != value0 or e.value[keys[0]][key1] >= value1
            elif '!=' in part0 and '<=' in part1:
                key0, value0 = part0.split('!=', 1)
                key1, value1 = part1.split('<=', 1)
                filter0 = lambda e: e.value[keys[0]][key0]  != value0 or e.value[keys[0]][key1] <= value1
            elif '!=' in part0 and '!=' in part1:
                key0, value0 = part0.split('!=', 1)
                key1, value1 = part1.split('!=', 1)
                filter0 = lambda e: e.value[keys[0]][key0]  != value0 or e.value[keys[0]][key1] != value1
            elif '!=' in part0 and '=' in part1:
                key0, value0 = part0.split('!=', 1)
                key1, value1 = part1.split('=', 1)
                filter0 = lambda e: e.value[keys[0]][key0]  != value0 or e.value[keys[0]][key1] == value1
            elif '!=' in part0 and '>' in part1:
                key0, value0 = part0.split('!=', 1)
                key1, value1 = part1.split('>', 1)
                filter0 = lambda e: e.value[keys[0]][key0]  != value0 or e.value[keys[0]][key1] > value1
            elif '!=' in part0 and '<' in part1:
                key0, value0 = part0.split('!=', 1)
                key1, value1 = part1.split('<', 1)
                filter0 = lambda e: e.value[keys[0]][key0]  != value0 or e.value[keys[0]][key1] < value1
            elif '!=' in part0 and ':' in part1:
                key0, value0 = part0.split('!=', 1)
                key1, value1 = part1.split(':', 1)
                filter0 = lambda e: e.value[keys[0]][key0]  != value0 or value1 in e.value[keys[0]][key1]
            elif '!=' in part0 and '=' not in part1:
                key0, value0 = part0.split('!=', 1)
                filter0 = lambda e: e.value[keys[0]][key0] != value0 or e.value[keys[0]][part1] != None

            elif '=' in part0 and '>=' in part1:
                key0, value0 = part0.split('=', 1)
                key1, value1 = part1.split('>=', 1)
                filter0 = lambda e: e.value[keys[0]][key0]  == value0 or e.value[keys[0]][key1] >= value1
            elif '=' in part0 and '<=' in part1:
                key0, value0 = part0.split('=', 1)
                key1, value1 = part1.split('<=', 1)
                filter0 = lambda e: e.value[keys[0]][key0]  == value0 or e.value[keys[0]][key1] <= value1
            elif '=' in part0 and '!=' in part1:
                key0, value0 = part0.split('=', 1)
                key1, value1 = part1.split('!=', 1)
                filter0 = lambda e: e.value[keys[0]][key0]  == value0 or e.value[keys[0]][key1] != value1
            elif '=' in part0 and '=' in part1:
                key0, value0 = part0.split('=', 1)
                key1, value1 = part1.split('=', 1)
                filter0 = lambda e: e.value[keys[0]][key0]  == value0 or e.value[keys[0]][key1] == value1
            elif '=' in part0 and '>' in part1:
                key0, value0 = part0.split('=', 1)
                key1, value1 = part1.split('>', 1)
                filter0 = lambda e: e.value[keys[0]][key0]  == value0 or e.value[keys[0]][key1] > value1
            elif '=' in part0 and '<' in part1:
                key0, value0 = part0.split('=', 1)
                key1, value1 = part1.split('<', 1)
                filter0 = lambda e: e.value[keys[0]][key0]  == value0 or e.value[keys[0]][key1] < value1
            elif '=' in part0 and ':' in part1:
                key0, value0 = part0.split('=', 1)
                key1, value1 = part1.split(':', 1)
                filter0 = lambda e: e.value[keys[0]][key0]  == value0 or value1 in e.value[keys[0]][key1]
            elif '=' in part0 and '=' not in part1:
                key0, value0 = part0.split('=', 1)
                filter0 = lambda e: e.value[keys[0]][key0] == value0 or e.value[keys[0]][part1] != None

            elif '>' in part0 and '>=' in part1:
                key0, value0 = part0.split('>', 1)
                key1, value1 = part1.split('>=', 1)
                filter0 = lambda e: e.value[keys[0]][key0]  > value0 or e.value[keys[0]][key1] >= value1
            elif '>' in part0 and '<=' in part1:
                key0, value0 = part0.split('>', 1)
                key1, value1 = part1.split('<=', 1)
                filter0 = lambda e: e.value[keys[0]][key0]  > value0 or e.value[keys[0]][key1] <= value1
            elif '>' in part0 and '!=' in part1:
                key0, value0 = part0.split('>', 1)
                key1, value1 = part1.split('!=', 1)
                filter0 = lambda e: e.value[keys[0]][key0] > value0 or e.value[keys[0]][key1] != value1
            elif '>' in part0 and '=' in part1:
                key0, value0 = part0.split('>', 1)
                key1, value1 = part1.split('=', 1)
                filter0 = lambda e: e.value[keys[0]][key0] > value0 or e.value[keys[0]][key1] == value1
            elif '>' in part0 and '>' in part1:
                key0, value0 = part0.split('>', 1)
                key1, value1 = part1.split('>', 1)
                filter0 = lambda e: e.value[keys[0]][key0] > value0 or e.value[keys[0]][key1] > value1
            elif '>' in part0 and '<' in part1:
                key0, value0 = part0.split('>', 1)
                key1, value1 = part1.split('<', 1)
                filter0 = lambda e: e.value[keys[0]][key0] > value0 or e.value[keys[0]][key1] < value1
            elif '>' in part0 and ':' in part1:
                key0, value0 = part0.split('>', 1)
                key1, value1 = part1.split(':', 1)
                filter0 = lambda e: e.value[keys[0]][key0] > value0 or value1 in e.value[keys[0]][key1]
            elif '>' in part0 and '=' not in part1:
                key0, value0 = part0.split('>', 1)
                filter0 = lambda e: e.value[keys[0]][key0] > value0 or e.value[keys[0]][part1] != None


            elif '<' in part0 and '>=' in part1:
                key0, value0 = part0.split('<', 1)
                key1, value1 = part1.split('>=', 1)
                filter0 = lambda e: e.value[keys[0]][key0]  < value0 or e.value[keys[0]][key1] >= value1
            elif '<' in part0 and '<=' in part1:
                key0, value0 = part0.split('<', 1)
                key1, value1 = part1.split('<=', 1)
                filter0 = lambda e: e.value[keys[0]][key0]  < value0 or e.value[keys[0]][key1] <= value1
            elif '<' in part0 and '!=' in part1:
                key0, value0 = part0.split('<', 1)
                key1, value1 = part1.split('!=', 1)
                filter0 = lambda e: e.value[keys[0]][key0] < value0 or e.value[keys[0]][key1] != value1
            elif '<' in part0 and '=' in part1:
                key0, value0 = part0.split('<', 1)
                key1, value1 = part1.split('=', 1)
                filter0 = lambda e: e.value[keys[0]][key0] < value0 or e.value[keys[0]][key1] == value1
            elif '<' in part0 and '>' in part1:
                key0, value0 = part0.split('<', 1)
                key1, value1 = part1.split('>', 1)
                filter0 = lambda e: e.value[keys[0]][key0] < value0 or e.value[keys[0]][key1] > value1
            elif '<' in part0 and '<' in part1:
                key0, value0 = part0.split('<', 1)
                key1, value1 = part1.split('<', 1)
                filter0 = lambda e: e.value[keys[0]][key0] < value0 or e.value[keys[0]][key1] < value1
            elif '<' in part0 and ':' in part1:
                key0, value0 = part0.split('<', 1)
                key1, value1 = part1.split(':', 1)
                filter0 = lambda e: e.value[keys[0]][key0] < value0 or value1 in e.value[keys[0]][key1]
            elif '<' in part0 and '=' not in part1:
                key0, value0 = part0.split('<', 1)
                filter0 = lambda e: e.value[keys[0]][key0] < value0 or e.value[keys[0]][part1] != None

            elif ':' in part0 and '>=' in part1:
                key0, value0 = part0.split(':', 1)
                key1, value1 = part1.split('>=', 1)
                filter0 = lambda e: value0 in e.value[keys[0]][key0] or e.value[keys[0]][key1] >= value1
            elif ':' in part0 and '<=' in part1:
                key0, value0 = part0.split('<', 1)
                key1, value1 = part1.split('<=', 1)
                filter0 = lambda e: value0 in e.value[keys[0]][key0] or e.value[keys[0]][key1] <= value1
            elif ':' in part0 and '!=' in part1:
                key0, value0 = part0.split('<', 1)
                key1, value1 = part1.split('!=', 1)
                filter0 = lambda e: value0 in e.value[keys[0]][key0] or e.value[keys[0]][key1] != value1
            elif ':' in part0 and '=' in part1:
                key0, value0 = part0.split('<', 1)
                key1, value1 = part1.split('=', 1)
                filter0 = lambda e: value0 in e.value[keys[0]][key0] or e.value[keys[0]][key1] == value1
            elif ':' in part0 and '>' in part1:
                key0, value0 = part0.split('<', 1)
                key1, value1 = part1.split('>', 1)
                filter0 = lambda e: value0 in e.value[keys[0]][key0] or e.value[keys[0]][key1] > value1
            elif ':' in part0 and '<' in part1:
                key0, value0 = part0.split('<', 1)
                key1, value1 = part1.split('<', 1)
                filter0 = lambda e: value0 in e.value[keys[0]][key0] or e.value[keys[0]][key1] < value1
            elif ':' in part0 and ':' in part1:
                key0, value0 = part0.split('<', 1)
                key1, value1 = part1.split(':', 1)
                filter0 = lambda e: value0 in e.value[keys[0]][key0] or value1 in e.value[keys[0]][key1]
            elif ':' in part0 and '=' not in part1:
                key0, value0 = part0.split(':', 1)
                filter0 = lambda e: value0 in e.value[keys[0]][key0] or e.value[keys[0]][part1] != None
            else:
                raise Exception('not implemented!')

            elems = select(e for e in self.store).filter(filter0)

        else:
            if '>=' in keys[1]:
                key, value = keys[1].split('>=', 1)
                elems = select(e for e in self.store if e.value[keys[0]][key] >= float(value))
            elif '<=' in keys[1]:
                key, value = keys[1].split('<=', 1)
                elems = select(e for e in self.store if e.value[keys[0]][key] <= float(value))
            elif '!=' in keys[1]:
                key, value = keys[1].split('!=', 1)
                elems = select(e for e in self.store if e.value[keys[0]][key] != value)
            elif '=' in keys[1]:
                key, value = keys[1].split('=', 1)
                elems = select(e for e in self.store if e.value[keys[0]][key] == value)
            elif '>' in keys[1]:
                key, value = keys[1].split('>', 1)
                elems = select(e for e in self.store if e.value[keys[0]][key] > float(value))
            elif '<' in keys[1]:
                key, value = keys[1].split('<', 1)
                elems = select(e for e in self.store if e.value[keys[0]][key] < float(value))
            elif ':' in keys[1]:
                key, value = keys[1].split(':', 1)
                elems = select(e for e in self.store if value in e.value[keys[0]][key])
            else:
                elems = select(e for e in self.store if keys[1] in e.value[keys[0]])
        return elems

    def _query_elems2(self, *keys):
        if '&&' in keys[2]:
            part0, part1 = keys[2].split('&&', 1)
            if '>=' in part0:
                key0, value0 = part0.split('>=', 1)
                filter1 = lambda e: e.value[keys[0]][keys[1]][key0] >= float(value0)
            elif '<=' in part0:
                key0, value0 = part0.split('<=', 1)
                filter1 = lambda e: e.value[keys[0]][keys[1]][key0] <= float(value0)
            elif '!=' in part0:
                key0, value0 = part0.split('!=', 1)
                filter1 = lambda e: e.value[keys[0]][keys[1]][key0]  != value0
            elif '=' in part0:
                key0, value0 = part0.split('=', 1)
                filter1 = lambda e: e.value[keys[0]][keys[1]][key0]  == value0
            elif '>' in part0:
                key0, value0 = part0.split('>', 1)
                filter1 = lambda e: e.value[keys[0]][keys[1]][key0]  > float(value0)
            elif '=' in part0:
                key0, value0 = part0.split('<', 1)
                filter1 = lambda e: e.value[keys[0]][keys[1]][key0]  < float(value0)
            elif ':' in part0:
                key0, value0 = part0.split(':', 1)
                filter1 = lambda e: value0 in e.value[keys[0]][keys[1]][key0]
            else:
                filter1 = lambda e: e.value[keys[0]][keys[1]][part0] != None


            if '>=' in part1:
                key1, value1 = part1.split('>=', 1)
                filter2 = lambda e: e.value[keys[0]][keys[1]][key1]  >= float(value1)
            elif '<=' in part1:
                key1, value1 = part1.split('<=', 1)
                filter2 = lambda e: e.value[keys[0]][keys[1]][key1]  <= float(value1)
            elif '!=' in part1:
                key1, value1 = part1.split('!=', 1)
                filter2 = lambda e: e.value[keys[0]][keys[1]][key1]  != value1
            elif '=' in part1:
                key1, value1 = part1.split('=', 1)
                filter2 = lambda e: e.value[keys[0]][keys[1]][key1]  == value1
            elif '>' in part1:
                key1, value1 = part1.split('>', 1)
                filter2 = lambda e: e.value[keys[0]][keys[1]][key1]  > float(value1)
            elif '<' in part1:
                key1, value1 = part1.split('<', 1)
                filter2 = lambda e: e.value[keys[0]][keys[1]][key1]  < float(value1)
            elif ':' in part1:
                key1, value1 = part1.split(':', 1)
                filter2 = lambda e: value1 in e.value[keys[0]][keys[1]][key1] 
            else:
                filter2 = lambda e: e.value[keys[0]][keys[1]][part1] != None

            elems = select(e for e in self.store).filter(filter1).filter(filter2)

        elif '||' in keys[2]:
            part0, part1 = keys[2].split('||', 1)
            if '>' in part0 or '<' in part0 or '!' in part0 or ':' in part0:
                raise Exception('not implemented!')
            if '>' in part1 or '<' in part1 or '!' in part1 or ':' in part1:
                raise Exception('not implemented!')
                
            if '=' in part0 and '=' in part1:
                key0, value0 = part0.split('=', 1)
                key1, value1 = part1.split('=', 1)
                filter0 = lambda e: e.value[keys[0]][keys[1]][key0]  == value0 or e.value[keys[0]][keys[1]][key1] == value1
            elif '=' in part0 and '=' not in part1:
                key0, value0 = part0.split('=', 1)
                filter0 = lambda e: e.value[keys[0]][keys[1]][key0]  == value0 or e.value[keys[0]][keys[1]][part1] != None
            elif '=' not in part0 and '=' in part1:
                key1, value1 = part1.split('=', 1)
                filter0 = lambda e: e.value[keys[0]][keys[1]][part0] != None or e.value[keys[0]][keys[1]][key1] == value1
            else:
                filter0 = lambda e: e.value[keys[0]][keys[1]][part0] != None or e.value[keys[0]][keys[1]][part1] != None
            elems = select(e for e in self.store).filter(filter0)
        else:
            if '>=' in keys[2]:
                key, value = keys[2].split('>=', 1)
                elems = select(e for e in self.store if  e.value[keys[0]][keys[1]][key] >= value)
            elif '<=' in keys[2]:
                key, value = keys[2].split('<=', 1)
                elems = select(e for e in self.store if  e.value[keys[0]][keys[1]][key] <= value)
            elif '!=' in keys[2]:
                key, value = keys[2].split('!=', 1)
                elems = select(e for e in self.store if  e.value[keys[0]][keys[1]][key] != value)
            elif '=' in keys[2]:
                key, value = keys[2].split('=', 1)
                elems = select(e for e in self.store if  e.value[keys[0]][keys[1]][key] == value)
            elif '>' in keys[2]:
                key, value = keys[2].split('>', 1)
                elems = select(e for e in self.store if  e.value[keys[0]][keys[1]][key] > value)
            elif '<' in keys[2]:
                key, value = keys[2].split('<', 1)
                elems = select(e for e in self.store if  e.value[keys[0]][keys[1]][key] < value)
            elif ':' in keys[2]:
                key, value = keys[2].split(':', 1)
                elems = select(e for e in self.store if  value in e.value[keys[0]][keys[1]][key])
            else:
                elems = select(e for e in self.store if keys[2] in e.value[keys[0]][keys[1]])
        return elems

    def _query_elems3(self, *keys):
        if '&&' in keys[3]:
            part0, part1 = keys[3].split('&&', 1)
            if '>=' in part0:
                key0, value0 = part0.split('>=', 1)
                filter1 = lambda e: e.value[keys[0]][keys[1]][keys[2]][key0] >= float(value0)
            elif '<=' in part0:
                key0, value0 = part0.split('<=', 1)
                filter1 = lambda e: e.value[keys[0]][keys[1]][keys[2]][key0] <= float(value0)
            elif '!=' in part0:
                key0, value0 = part0.split('!=', 1)
                filter1 = lambda e: e.value[keys[0]][keys[1]][keys[2]][key0]  != value0
            elif '=' in part0:
                key0, value0 = part0.split('=', 1)
                filter1 = lambda e: e.value[keys[0]][keys[1]][keys[2]][key0]  == value0
            elif '>' in part0:
                key0, value0 = part0.split('>', 1)
                filter1 = lambda e: e.value[keys[0]][keys[1]][keys[2]][key0]  > float(value0)
            elif '=' in part0:
                key0, value0 = part0.split('<', 1)
                filter1 = lambda e: e.value[keys[0]][keys[1]][keys[2]][key0]  < float(value0)
            elif ':' in part0:
                key0, value0 = part0.split(':', 1)
                filter1 = lambda e: value0 in e.value[keys[0]][keys[1]][keys[2]][key0]
            else:
                filter1 = lambda e: e.value[keys[0]][keys[1]][keys[2]][part0] != None


            if '>=' in part1:
                key1, value1 = part1.split('>=', 1)
                filter2 = lambda e: e.value[keys[0]][keys[1]][keys[2]][key1]  >= float(value1)
            elif '<=' in part1:
                key1, value1 = part1.split('<=', 1)
                filter2 = lambda e: e.value[keys[0]][keys[1]][keys[2]][key1]  <= float(value1)
            elif '!=' in part1:
                key1, value1 = part1.split('!=', 1)
                filter2 = lambda e: e.value[keys[0]][keys[1]][keys[2]][key1]  != value1
            elif '=' in part1:
                key1, value1 = part1.split('=', 1)
                filter2 = lambda e: e.value[keys[0]][keys[1]][keys[2]][key1]  == value1
            elif '>' in part1:
                key1, value1 = part1.split('>', 1)
                filter2 = lambda e: e.value[keys[0]][keys[1]][keys[2]][key1]  > float(value1)
            elif '<' in part1:
                key1, value1 = part1.split('<', 1)
                filter2 = lambda e: e.value[keys[0]][keys[1]][keys[2]][key1]  < float(value1)
            elif ':' in part1:
                key1, value1 = part1.split(':', 1)
                filter2 = lambda e: value1 in e.value[keys[0]][keys[1]][keys[2]][key1] 
            else:
                filter2 = lambda e: e.value[keys[0]][keys[1]][keys[2]][part1] != None

            elems = select(e for e in self.store).filter(filter1).filter(filter2)

        elif '||' in keys[3]:
            part0, part1 = keys[3].split('||', 1)
            if '>' in part0 or '<' in part0 or '!' in part0 or ':' in part0:
                raise Exception('not implemented!')
            if '>' in part1 or '<' in part1 or '!' in part1 or ':' in part1:
                raise Exception('not implemented!')

            if '=' in part0 and '=' in part1:
                key0, value0 = part0.split('=', 1)
                key1, value1 = part1.split('=', 1)
                filter0 = lambda e: e.value[keys[0]][keys[1]][keys[2]][key0]  == value0 or e.value[keys[0]][keys[1]][keys[2]][key1] == value1
            elif '=' in part0 and '=' not in part1:
                key0, value0 = part0.split('=', 1)
                filter0 = lambda e: e.value[keys[0]][keys[1]][keys[2]][key0]  == value0 or e.value[keys[0]][keys[1]][keys[2]][part1] != None
            elif '=' not in part0 and '=' in part1:
                key1, value1 = part1.split('=', 1)
                filter0 = lambda e: e.value[keys[0]][keys[1]][keys[2]][part0] != None or e.value[keys[0]][keys[1]][keys[2]][key1] == value1
            else:
                filter0 = lambda e: e.value[keys[0]][keys[1]][keys[2]][part0] != None or e.value[keys[0]][keys[1]][keys[2]][part1] != None
            elems = select(e for e in self.store).filter(filter0)
        else:
            if '>=' in keys[3]:
                key, value = keys[3].split('>=', 1)
                elems = select(e for e in self.store if e.value[keys[0]][keys[1]][keys[2]][key] >= value)
            elif '<=' in keys[3]:
                key, value = keys[3].split('<=', 1)
                elems = select(e for e in self.store if e.value[keys[0]][keys[1]][keys[2]][key] <= value)
            elif '!=' in keys[3]:
                key, value = keys[3].split('!=', 1)
                elems = select(e for e in self.store if e.value[keys[0]][keys[1]][keys[2]][key] != value)
            elif '=' in keys[3]:
                key, value = keys[3].split('=', 1)
                elems = select(e for e in self.store if e.value[keys[0]][keys[1]][keys[2]][key] == value)
            elif '>' in keys[3]:
                key, value = keys[3].split('>', 1)
                elems = select(e for e in self.store if e.value[keys[0]][keys[1]][keys[2]][key] > value)
            elif '<' in keys[3]:
                key, value = keys[3].split('<', 1)
                elems = select(e for e in self.store if e.value[keys[0]][keys[1]][keys[2]][key] < value)
            elif ':' in keys[3]:
                key, value = keys[3].split(':', 1)
                elems = select(e for e in self.store if value in e.value[keys[0]][keys[1]][keys[2]][key])
            else:
                elems = select(e for e in self.store if keys[3] in e.value[keys[0]][keys[1]][keys[2]])
        return elems
    @db_session
    def query_value(self, *keys, for_update=False):
        elems = self._query_value(*keys, for_update=for_update)
        return StoreMetas(elems, store=self.store)

    def adjust_slice(self, elems, for_update=False):
        if for_update:
            elems = elems.for_update()
        begin, end = self.begin, self.end
        if begin and end:
            if begin < 0:
                begin = len(self) + begin
            if end < 0:
                end = len(self) + end
            if begin > end:
                begin, end = end, end
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


class Tiger(Store):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        Store.register_attr('test')

    def test(self):
        print('test')


def test(t):
    t.a = {
        'name': 'king'
    }
    print(t['name=king'].name)


if __name__ == "__main__":
    import time
    # t = Tiger(provider='postgres', user='dameng', password='pythonic',
    #           database='mytest', port=5432, host='127.0.0.1')
    # t = Tiger(provider='mysql', user='root', password='dangerous123',
    #           database='mytest', port=8306, host='127.0.0.1')
    t = Tiger('sqlite')
    # t.slice(0,10)
    # print(t['*'])
    # print('.....')

    # t.slice(10,15)
    # print(t['*']['like'])
    # t.test()
    # t.add({'hello': 1})
    # t.add({'hello': 2})
    # print(t['*'])
    # print(t.sum(lambda e: e.value['hello'] == 'world', 'hello') )
    # print(sum[t['hello=1']['hello']])
    # print(len(t))
    # print(sum(t['hello=1']['hello']))

    # import time
    # time.sleep(60)
    t.a = {"a1": {"b1": {"c1": {"d1": 14, "d2": ["123", "ab"]}, "c2":30}}, "a2": {"b2": [], "b22": {"c22": 123}}, "a3": []}
    # print(t.query_keys("a3"))
    # print(t.query_keys("a1", "b1"))
    # print(t.query_keys("a2", "b2"))
    # print(t['*', "a3"])
    print(t.query_value("a1", "b1", "c1", "d1=14"))
    print(t["a1", "b1", "c1", "d1=14"])
    print(t["a1,b1,c1,d1=14"])
    print(t["a1,b1,c1,d1=14"]['a1'])
    # time.sleep(1)
    for e in t["a1,b1,c1,d1=14"]:
        print(e['a1']['b1']['c1'])
        e['m1'] = 10
    # time.sleep(1)
    for e in t["a1,b1,c1,d1=14"]:
        print(e)
    t["a1,b1,c1,d1=14"]['m1'] = 20
    # time.sleep(1)
    for e in t["a1,b1,c1,d1=14"]:
        print(e)
    # print(t["a1,b1,c1,d1=14"]['a1']['b1'])
    # t["a1,b1,c1,d1=14"]['a1'] = 15
    # print(t.a)
    # print(t.query_value("a1", "b1", "c2=10"))
    t.a = {"a1": {"b1": {"c1": {"d1": 14, "d2": ["123", "ab"]}, "c2":30}}, "a2": {"b2": [], "b22": {"c22": 123}}, "m2": [{"n1": "hello"}, {"n2": "world"}]}
    print(type(t['m2','n2']))
    print(type(t['a1','b1']))
    t.b1 = {'a1': 'h1', 'z1':1}
    t.b2 = {'a1': 'h1', 'z1':2}
    t.b3 = {'a1': 'h1', 'z1':40}
    t.b4 = {"t":{'a1': 'h1', 'z1': 100}}
    t.b5 = {"t":{'a1': 'h1', 'z1': 120}}
    t.b6 = {"t":{'m': {'a1': 'h2', 'z1': 120}}}
    t.b7 = {"t":{'m': {'a1': 'h1', 'z1': 5}}}
    t.b8 = {"t":{'m': { 'n': {'a1': 'h1', 'z1': 5}}}}
    t.b8 = {"t":{'m': { 'n': {'a1': 'h1', 'z2': 5}}}}
    print(t['t', 'm','n','a1=h1&&z2'])
    t.c1 = "hello"
    t.c2 = "hello2"
    t.c3 = "hello3"
    t.hello1 = 'abc'
    t.hello2 = 'abc'
    t.hello3 = 'abc'
    t.hello11 = 'abc'
    print('>>>>>>')
    # print(t['c1||c2||c3'])
    print(t['^he'])
    print('????')
    del t['^hello1']
    print(t['^he'])
    t.abc = {"hello": "world", "meng": "chao"}
    t.abc = {"hello": "world", "men": "chao2"}
    print('>>>????1')
    print(t['*'].value)
    print('>>>????2')
    print(t['t,'])



