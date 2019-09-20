
from pony.orm import (Database, Json, PrimaryKey, Required, commit, count,
                      db_session, delete, desc, select, raw_sql)

# filter_index
def fi(data): 
    if isinstance(data, int): 
        return int(data)
    if isinstance(data, str) and data[0] in '0123456789' :
        return int(data)
    else: 
        return f'"{data}"'

def parse_filter(data):
    for op in ['>=', '<=', '!=', '=', '>', '<', '!:', ':', '?']:
        if op in data[-1]:
            k, v = data[-1].split(op, 1)
            if len(data) == 1:
                if op == '?':
                    return f'e.value[{fi(k)}] != None'
                filter_map = {
                    '>=':  f'e.value[{fi(k)}] >= {v}',
                    '<=':  f'e.value[{fi(k)}] <= {v}',
                    '!=': f'e.value[{fi(k)}] != {fi(v)}',
                    '=': f'e.value[{fi(k)}] == {fi(v)}',
                    '>': f'e.value[{fi(k)}] > {v}',
                    '<': f'e.value[{fi(k)}] < {v}',
                    '!:': f'{fi(v)} not in e.value[{fi(k)}]',
                    ':': f'{fi(v)} in e.value[{fi(k)}]',
                }
            elif len(data) == 2:
                if op == '?':
                    return f'e.value[{fi(data[-2])}][{fi(k)}] != None'
                filter_map = {
                    '>=':  f'e.value[{fi(data[-2])}][{fi(k)}] >= {v}',
                    '<=':  f'e.value[{fi(data[-2])}][{fi(k)}] <= {v}',
                    '!=': f'e.value[{fi(data[-2])}][{fi(k)}] != {fi(v)}',
                    '=': f'e.value[{fi(data[-2])}][{fi(k)}] == {fi(v)}',
                    '>': f'e.value[{fi(data[-2])}][{fi(k)}] > {v}',
                    '<': f'e.value[{fi(data[-2])}][{fi(k)}] < {v}',
                    '!:': f'{fi(v)} not in e.value[{fi(data[-2])}][{fi(k)}]',
                    ':': f'{fi(v)} in e.value[{fi(data[-2])}][{fi(k)}]',
                }
            elif len(data) == 3:
                if op == '?':
                    return f'e.value[{fi(data[-3])}][{fi(data[-2])}][{fi(k)}] != None'
                filter_map = {
                    '>=':  f'e.value[{fi(data[-3])}][{fi(data[-2])}][{fi(k)}] >= {v}',
                    '<=':  f'e.value[{fi(data[-3])}][{fi(data[-2])}][{fi(k)}] <= {v}',
                    '!=': f'e.value[{fi(data[-3])}][{fi(data[-2])}][{fi(k)}] != {fi(v)}',
                    '=': f'e.value[{fi(data[-3])}][{fi(data[-2])}][{fi(k)}] == {fi(v)}',
                    '>': f'e.value[{fi(data[-3])}][{fi(data[-2])}][{fi(k)}] > {v}',
                    '<': f'e.value[{fi(data[-3])}][{fi(data[-2])}][{fi(k)}] < {v}',
                    '!:': f'{fi(v)} not in e.value[{fi(data[-3])}][{fi(data[-2])}][{fi(k)}]',
                    ':': f'{fi(v)} in e.value[{fi(data[-3])}][{fi(data[-2])}][{fi(k)}]',
                }
            elif len(data) == 4:
                if op == '?':
                    return f'e.value[{fi(data[-4])}][{fi(data[-3])}][{fi(data[-2])}][{fi(k)}] != None'
                filter_map = {
                    '>=':  f'e.value[{fi(data[-4])}][{fi(data[-3])}][{fi(data[-2])}][{fi(k)}] >= {v}',
                    '<=':  f'e.value[{fi(data[-4])}][{fi(data[-3])}][{fi(data[-2])}][{fi(k)}] <= {v}',
                    '!=': f'e.value[{fi(data[-4])}][{fi(data[-3])}][{fi(data[-2])}][{fi(k)}] != {fi(v)}',
                    '=': f'e.value[{fi(data[-4])}][{fi(data[-3])}][{fi(data[-2])}][{fi(k)}] == {fi(v)}',
                    '>': f'e.value[{fi(data[-4])}][{fi(data[-3])}][{fi(data[-2])}][{fi(k)}] > {v}',
                    '<': f'e.value[{fi(data[-4])}][{fi(data[-3])}][{fi(data[-2])}][{fi(k)}] < {v}',
                    '!:': f'{fi(v)} not in e.value[{fi(data[-4])}][{fi(data[-3])}][{fi(data[-2])}][{fi(k)}]',
                    ':': f'{fi(v)} in e.value[{fi(data[-4])}][{fi(data[-3])}][{fi(data[-2])}][{fi(k)}]',
                }
            else:
                raise Exception('Not Implemented!')
            return filter_map.get(op)
    
    raise Exception('Not Implemented!')


def parse(condition):
    if '||' in condition:
        conda, condb = condition.split('||', 1)
        conda, condb = conda.strip(), condb.strip()
        # filtera = filterb = None

        # if '||' in conda or '&&' in conda:
        filtera = parse(conda)

        # if '||' in condb or '&&' in condb:
        filterb = parse(condb)

        if filtera and filterb:
            return f'{filtera} or {filterb}'
        if filtera:
            data = condb.split('.') if '.' in condb else [condb]
            filterb =  parse_filter([d.strip() for d in data])          
            return f'{filtera} or {filterb}'
        if filterb:
            data = conda.split('.') if '.' in conda else [conda]
            filtera =  parse_filter([d.strip() for d in data])          
            return f'{filtera} or {filterb}'
        else:
            data = conda.split('.') if '.' in conda else [conda]
            filtera =  parse_filter([d.strip() for d in data])          
            data = condb.split('.') if '.' in condb else [condb]
            filterb =  parse_filter([d.strip() for d in data])          
            return f'{filtera} or {filterb}'

    if '&&' in condition:
        conda, condb = condition.split('&&', 1)
        conda, condb = conda.strip(), condb.strip()
        filtera = filterb = None

        if '||' in conda or '&&' in conda:
            filtera = parse(conda)

        if '||' in condb or '&&' in condb:
            filterb = parse(condb)

        if filtera and filterb:
            return f'{filtera} and {filterb}'
        if filtera:
            data = condb.split('.') if '.' in condb else [condb]
            filterb =  parse_filter([d.strip() for d in data])          
            return f'{filtera} and {filterb}'
        if filterb:
            data = conda.split('.') if '.' in conda else [conda]
            filtera =  parse_filter([d.strip() for d in data])          
            return f'{filtera} and {filterb}'
        else:
            data = conda.split('.') if '.' in conda else [conda]
            filtera =  parse_filter([d.strip() for d in data])          
            data = condb.split('.') if '.' in condb else [condb]
            filterb =  parse_filter([d.strip() for d in data])          
            return f'{filtera} and {filterb}'
        ####
    if condition=='*':
        return
    if '%' in condition:
        return raw_sql(f'e.key like "{condition}"')
    if condition[0] == '(' and condition[-1] == ')':
        return f'"{condition[1:-1]}" in e.key'
    if condition[0] == ')' and condition[-1] == '(':
        return f'"{condition[1:-1]}" not in e.key'
    if condition[0] == '^' and condition[-1] == '$':
        return f'e.key == "{condition[1:-1]}"'
    if condition[0] == '^':
        return f'e.key.startswith("{condition[1:]}")'
    if condition[-1] == '$':
        return f'e.key.endswith("{condition[:-1]}")'
    if condition[-1] == '?':
        if '.' in condition:
            data = condition.split('.')
            return parse_filter([d.strip() for d in data])          
        else:
            return f'e.value[{fi(condition[:-1])}] != None'


    if '=' not in condition and '>' not in condition and '<' not in condition and \
       '!' not in condition and ':' not in condition and '.' not in condition:
        return f'e.key == "{condition}"'

    data = condition.split('.') if '.' in condition else [condition]
    return parse_filter([d.strip() for d in data])          
