from pony.orm import Database, Required, PrimaryKey, Json, db_session, select, commit, desc, delete
from datetime import datetime
from copy import copy
import os
import uuid
import json

class StoreMetas:
    def __init__(self, elems, store=None):
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

        if key in ['store','id', 'key', 'value', 'create', 'update']: 
            return [elem.key for elem in self.elems]
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
        return "id: {}, key: {}, value: {}, create: {}, update: {}".format(self.id, self.key, self.value,
                                                                           self.create, self.update)

    @db_session
    def __assign__(self, value):
        elem = select(e for e in self.store if e.id == self.id).order_by(lambda o: desc(o.create)).first()
        if elem is None:
            raise Exception('elem not found')
        else:
            elem.value = value
            elem.update_at = datetime.utcnow()
            self.value = elem.value
            self.update = elem.update.strftime("%Y-%m-%dT%H:%M:%S")

    @db_session
    def __setattr__(self, key, value):
        if key in ['store','id', 'key', 'value', 'create', 'update'] or key.startswith('_'):
            return super().__setattr__(key, value)
        elem = select(e for e in self.store if e.id == self.id).order_by(lambda o: desc(o.create)).first()
        if elem is None:
            raise Exception('elem not found')
        else:
            if isinstance(elem.value, dict):
                elem.value[key] = value
                elem.update_at = datetime.utcnow()
                self.value = elem.value
                self.update = elem.update.strftime("%Y-%m-%dT%H:%M:%S")
            else:
                raise Exception('value not dict!')

    @db_session
    def __getattribute__(self, key):
        if key in ['store','id', 'key', 'value', 'create', 'update'] or key.startswith('_'):
            return object.__getattribute__(self, key)

        elem = select(e for e in self.store if e.id == self.id).order_by(lambda o: desc(o.create)).first()
        if elem:
            if isinstance(elem.value, dict):
                return elem.value.get(key)

    @db_session
    def __setitem__(self, key, value):
        elem = select(e for e in self.store if e.id == self.id).order_by(lambda o: desc(o.create)).first()
        if elem is None:
            raise Exception('elem not found')
        else:
            if isinstance(elem.value, dict) or \
               (isinstance(key, int) and isinstance(elem.value, list)):
                elem.value[key] = value
                elem.update_at = datetime.utcnow()
                self.value = elem.value
                self.update = elem.update.strftime("%Y-%m-%dT%H:%M:%S")
            else:
                raise Exception('value not dict!')

    @db_session
    def __getitem__(self, key):
        elem = select(e for e in self.store if e.id == self.id).order_by(lambda o: desc(o.create)).first()
        if elem:
            if isinstance(elem.value, dict)or \
               (isinstance(key, int) and isinstance(elem.value, list)) or \
               (isinstance(key, int) and isinstance(elem.value, str)) :
                return elem.value[key]
    


class Store(object):
    def __init__(self,
                 provider=None, user=None, password=None,
                 host=None, port=None, database=None, filename = None,
                 begin=None, end=None):
                
        if provider == 'postgres':
            self.database = Database(provider, user=user or 'postgres', password=password or 'postgres', 
                                     host=host or 'localhost', port=port or 5432, database=database or 'postgres')
        elif provider == 'mysql':
            self.database = Database(provider, user=user or 'root', password=password or 'dangerous', 
                                     host=host or 'localhost', port=port or 3306, database=database or 'mysql')
        elif provider == 'sqlite':
            if not filename:
                filename = 'database.sqlite'
            if not filename.startswith('/'):
                filename = os.getcwd()+'/' + filename
            self.database = Database(provider, filename=filename, create_db=True)
        else:
            raise Exception('not implemented!')

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

    @db_session
    def __setattr__(self, key, value):
        if key in ['store', 'database', 'tablename', 'begin', 'end', 'add', 'query_keys'] or key.startswith('_'):
            return super().__setattr__(key, value)
        item = select(e for e in self.store if e.key == key).order_by(lambda o: desc(o.create)).first()
        if item is None:
            self.store(key=key, value=value)
        else:
            item.value = value
            item.update_at = datetime.utcnow()

    @db_session
    def __getattribute__(self, key):
        if key in ['store', 'database', 'tablename', 'begin', 'end', 'add', 'query_keys'] or key.startswith('_'):
            return object.__getattribute__(self, key)

        elem = select(e for e in self.store if e.key == key).order_by(lambda o: desc(o.create)).first()
        if elem:
            return StoreMeta(elem, store=self.store)
        return None

    @db_session
    def __setitem__(self, key, value):
        if isinstance(key, slice):
            raise Exception('not implemented!')
        elif isinstance(key, tuple):
            if len(key) == 2:
                elems = self._getitem_query_tuple(key)
                if elems:
                    now = datetime.utcnow()
                    for elem in elems:
                        elem.value = value
                        elem.update_at = now
                    return
            raise Exception('not implemented!')
        elif isinstance(key, str):

            if '=' in key or ':' in key:
                updated_key = ['*', key]
                elems = self._getitem_query_tuple(updated_key)
                if elems:
                    now = datetime.utcnow()
                    for elem in elems:
                        elem.value = value
                        elem.update_at = now
                return

            item = select(e for e in self.store if e.key == key).order_by(lambda o: desc(o.create)).first()
            if item is None:
                self.store(key=key, value=value)
            else:
                item.value = value
                item.update_at = datetime.utcnow()

    @db_session
    def __getitem__(self, key):
        if isinstance(key, slice):
            raise Exception('not implemented!')
        elif isinstance(key, tuple):
            if len(key) == 2:
                elems = self._getitem_query_tuple(key)
                return StoreMetas(elems, store=self.store)
            raise Exception('not implemented!')
        elif isinstance(key, str):
            if '=' in key or ':' in key:
                updated_key = ['*', key]
                elems = self._getitem_query_tuple(updated_key)
                return StoreMetas(elems, store=self.store)
            elem = select(e for e in self.store if e.key == key).order_by(lambda o: desc(o.create)).first()
            if elem:
                return StoreMeta(elem, store=self.store)
        return []

    @db_session
    def __delitem__(self, key):
        if isinstance(key, slice):
            raise Exception('not implemented!')
        elif isinstance(key, tuple):
            if len(key) == 2:
                elems = self._getitem_query_tuple(key)
                for elem in elems:
                    elem.delete()
                return 
            raise Exception('not implemented!')
        elif isinstance(key, str):
            if '=' in key or ':' in key:
                updated_key = ['*', key]
                elems = self._getitem_query_tuple(updated_key)
                for elem in elems:
                    elem.delete()
                return 
            elem = select(e for e in self.store if e.key == key).order_by(lambda o: desc(o.create)).first()
            if elem:
                elem.delete()
                return
        raise Exception('not implemented!')




    @db_session
    def __delattr__(self, key):
        delete(e for e in self.store if e.key == key)


    @db_session
    def _getitem_query_tuple(self, key):
        if key[0] == '*':
            if '=' in key[1]:
                k, v = key[1].split('=', 1)
                elems = select(e for e in self.store if e.value[k] == v).order_by(lambda o: desc(o.create))
            elif ':' in key[1]:
                k, v = key[1].split(':', 1)
                elems = select(e for e in self.store if e.value[k] == v).order_by(lambda o: desc(o.create))
            else:
                elems = select(e for e in self.store if e.value[key[1]]).order_by(lambda o: desc(o.create))
        else:
            if '=' in key[1]:
                k, v = key[1].split('=', 1)
                elems = select(e for e in self.store if e.key == key[0] and e.value[k]==v).order_by(lambda o: desc(o.create))
            elif ':' in key[1]:
                k, v = key[1].split(':', 1)
                elems = select(e for e in self.store if e.key == key[0] and e.value[k]==v).order_by(lambda o: desc(o.create))
            else:
                elems = select(e for e in self.store if e.key == key[0] and e.value[key[1]]).order_by(lambda o: desc(o.create))
        if self.begin and self.end:
            elems = elems[self.begin:self.end]
        elif self.begin:
            elems = elems[self.begin:]
        elif self.end:
            elems = elems[:self.end]
        else:
            elems = elems[:]

        return elems

    @db_session
    def add(self, value):
        hex = uuid.uuid1().hex
        key = "store_{}".format(hex)
        self.store(key=key, value=value)
        return key

    @db_session
    def query_keys(self, *keys):
        lenkeys = len(keys)
        if lenkeys == 1:
            elems = select(e for e in self.store if e.value[keys[0]])
        elif lenkeys == 2:
            elems = select(e for e in self.store if e.value[keys[0]][keys[1]])
        elif lenkeys == 3:
            elems = select(e for e in self.store if e.value[keys[0]][keys[1]][keys[2]])
        else:
            raise Exception('not implemented!')

        if self.begin and self.end:
            elems = elems[self.begin:self.end]
        elif self.begin:
            elems = elems[self.begin:]
        elif self.end:
            elems = elems[:self.end]
        else:
            elems = elems[:]

        return StoreMetas(elems, store=self.store)


class Tiger(Store):
    pass

def test(t):
    t.a = {
        'name': 'king'
    }
    print(t['name=king'].name)

if __name__ == "__main__":
    t = Tiger(provider='mysql', user='root', password='dangerous123',
              database='mytest', port=8306, host='127.0.0.1')
    import time
    time.sleep(60)
            



