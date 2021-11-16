import re
import yaml

def convert_short_array_syntax(schema):

    if 'k8ssandra' not in schema:
        return schema
    if 'cassandra' not in schema['k8ssandra']:
        return schema

    dcs = {
        'datacenters': []
    }

    keys_to_delete = {}

    for k,v in schema['k8ssandra']['cassandra'].items():
        if 'datacenters' in k:
            keys_to_delete[k] = True
            m = re.match('^.+\[([0-9])\].*$', k)
            if m.groups():
                dcs['datacenters'].append({
                    'name': schema['k8ssandra']['cassandra'][k]['name'],
                    'size': schema['k8ssandra']['cassandra'][k]['size']
                })
    if dcs['datacenters']:
        schema['k8ssandra']['cassandra'].update(dcs)
        for k in keys_to_delete:
            del schema['k8ssandra']['cassandra'][k]
    return schema
