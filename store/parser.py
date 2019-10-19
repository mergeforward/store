from pony.orm import (Database, Json, PrimaryKey, Required, commit, count,
                      db_session, delete, desc, select, raw_sql)

# filter_index
def fi(data): 
    if isinstance(data, str):
        if data[0] in '0123456789.-+':
            try:
                value = int(data)
                return value
            except ValueError:
                try:
                    value = float(data)
                    return value
                except ValueError:
                    pass
        return f'"{data}"'
    if isinstance(data, float): 
        return float(data)
    if isinstance(data, int): 
        return int(data)
    return f'"{data}"'

# filter data
def fv(key):
    filter = ''
    for i in range(len(key)):
        filter = f'[{fi(key[-1-i])}]' + filter
    return filter

def parse_filter(data, column='data'):
    # parse json condition
    for op in ['>=', '<=', '>', '<', '!=', '==', '=',  '!:', ':', '?']:
        if op in data:
            # last for json key exists
            if op == '?':
                data = data[:-1]
                break
            k, v = data.split(op, 1)
            k = [d.strip() for d in k.split('.')] if '.' in k else [k]
            if op == '=':
                op += '='
            return  f'e.{column}{fv(k)} {op} {fi(v)}'

    # parse json key exists
    if '.' in data:
        key = data.split('.')
        key = [d.strip() for d in key]
    else:
        key = [data]
    return f'e.{column}{fv(key)} != None'

def ab_parse(conda, condb, op, column='data'):
        # if '||' in conda or '&&' in conda:
        filtera, filterb = parse(conda, column=column), parse(condb, column=column)

        if filtera and filterb:
            return f'{filtera} {op} {filterb}'
        if filtera:
            filterb =  parse(condb, column=column)          
            return f'{filtera} {op} {filterb}'
        if filterb:
            filtera =  parse(conda, column=column)          
            return f'{filtera} {op} {filterb}'
        filtera =  parse(conda, column=column)          
        filterb =  parse(condb, column=column)          
        return f'{filtera} {op} {filterb}'

def parse(condition, column="data"):
    if '||' in condition:
        conda, condb = condition.split('||', 1)
        # conda, condb = conda.strip(), condb.strip()
        return ab_parse(conda.strip(), condb.strip(), 'or', column=column)

    if '&&' in condition:
        conda, condb = condition.split('&&', 1)
        return ab_parse(conda.strip(), condb.strip(), 'and', column=column)
        ####

    ### primary key
    if condition=='*':
        return
    if '%' in condition:
        # not work in mysql right now
        return raw_sql(f'e.key like "{condition}"')
    if condition[0] == '(' and condition[-1] == ')':
        return f'"{condition[1:-1]}" in e.key'
    if condition[0] == ')' and condition[-1] == '(':
        return f'"{condition[1:-1]}" not in e.key'
    if condition[0] == '~':
        return f'e.key != "{condition[1:]}"'
    if condition[0] == '^' and condition[-1] == '$':
        return f'e.key == "{condition[1:-1]}"'
    if condition[0] == '^':
        return f'e.key.startswith("{condition[1:]}")'
    if condition[-1] == '$':
        return f'e.key.endswith("{condition[:-1]}")'

    if '=' not in condition and '>' not in condition and '<' not in condition and \
       '!' not in condition and ':' not in condition and '.' not in condition and '?' not in condition:
        return f'e.key == "{condition}"'

    # json key
    return parse_filter(condition, column=column)
