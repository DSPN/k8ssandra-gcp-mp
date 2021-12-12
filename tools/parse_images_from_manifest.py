import pprint
import os

import yaml

out = {
    'cassandra': '',
    'cassandra-config-builder': '',
    'cassandra-jmx-credentials-config': '',
    'cassandra-logging-sidecar': '',
    'stargate': '',
    'stargate-wait-for-cassandra': '',
    'reaper': '',
    'medusa': '',
    'prometheus': '',
    'cleaner': '',
    'cass-operator': '',
    'reaper-operator': '',
    'medusa-operator': '',
    'prometheus-operator': '',
    'grafana': '',
    'kube-prometheus-stack-grafana-side-car': '',
}

app_name = 'k8ssandra-mp'

def nested_value(d, t):
    c = d
    for i in t:
        c = c[i]
    return c

def find_container(d, t, name):
    container = [i for i in nested_value(d, t) if i['name'] == name]
    if container:
        return container[0]

class Handler:
    def __init__(self, doc):
        self.doc = doc

    def is_cass_operator(self):
        return self.doc['kind'] == 'Deployment' and \
            self.doc['metadata']['name'] == f'{app_name}-cass-operator'

    def handle_cass_operator(self):
        t = ('spec', 'template', 'spec', 'containers')
        container = find_container(self.doc, t, 'cass-operator')
        out['cass-operator'] = container['image']

    def is_cassandra(self):
        return self.doc['kind'] == 'CassandraDatacenter'

    def handle_cassandra(self):
        out['cassandra'] = self.doc['spec']['serverImage']

    def is_cassandra_config_builder(self):
        return self.doc['kind'] == 'CassandraDatacenter'

    def handle_cassandra_config_builder(self):
        out['cassandra-config-builder'] = self.doc['spec']['configBuilderImage']

    def is_cassandra_logging_sidecar(self):
        return self.doc['kind'] == 'CassandraDatacenter'

    def handle_cassandra_logging_sidecar(self):
        out['cassandra-logging-sidecar'] = self.doc['spec']['systemLoggerImage']

    def is_cassandra_jmx_credentials_config(self):
        return self.doc['kind'] == 'CassandraDatacenter'

    def handle_cassandra_jmx_credentials_config(self):
        t = ('spec', 'podTemplateSpec', 'spec', 'initContainers')
        container = find_container(self.doc, t, 'jmx-credentials')
        out['cassandra-jmx-credentials-config'] = container['image']

    def is_cleaner(self):
        return self.doc['kind'] == 'Job' and \
            self.doc['metadata']['name'] == f'{app_name}-cleaner-job-k8ssandra'

    def handle_cleaner(self):
        t = ('spec', 'template', 'spec', 'containers')
        container = find_container(self.doc, t, 'cleaner-job-k8ssandra')
        out['cleaner'] = container['image']

    def is_grafana(self):
        return self.doc['kind'] == 'Deployment' and \
            self.doc['metadata']['name'] == f'{app_name}-grafana'

    def handle_grafana(self):
        t = ('spec', 'template', 'spec', 'containers')
        container = find_container(self.doc, t, 'grafana')
        out['grafana'] = container['image']

    def is_kube_prometheus_stack_grafana_image_renderer(self):
        return False

    def handle_kube_prometheus_stack_grafana_image_renderer(self):
        pass

    def is_kube_prometheus_stack_grafana_init_chown_data(self):
        return False

    def handle_kube_prometheus_stack_grafana_init_chown_data(self):
        pass

    def is_kube_prometheus_stack_grafana_side_car(self):
        return self.doc['kind'] == 'Deployment' and \
            self.doc['metadata']['name'] == f'{app_name}-grafana'

    def handle_kube_prometheus_stack_grafana_side_car(self):
        t = ('spec', 'template', 'spec', 'containers')
        container = find_container(self.doc, t, 'grafana-sc-dashboard')
        out['kube-prometheus-stack-grafana-side-car'] = container['image']

    def is_medusa(self):
        return self.doc['kind'] == 'CassandraDatacenter'

    def handle_medusa(self):
        t = ('spec', 'podTemplateSpec', 'spec', 'containers')
        container = find_container(self.doc, t, 'medusa')
        out['medusa'] = container['image']

    def is_medusa_operator(self):
        return self.doc['kind'] == 'Deployment' and \
            self.doc['metadata']['name'] == f'{app_name}-medusa-operator'

    def handle_medusa_operator(self):
        t = ('spec', 'template', 'spec', 'containers')
        container = find_container(self.doc, t, 'medusa-operator')
        out['medusa-operator'] = container['image']

    def is_prometheus(self):
        return self.doc['kind'] == 'Prometheus'

    def handle_prometheus(self):
        out['prometheus'] = self.doc['spec']['image']

    def is_prometheus_operator(self):
        return self.doc['kind'] == 'Deployment' and \
            self.doc['metadata']['name'] == f'{app_name}-kube-promethe-operator'

    def handle_prometheus_operator(self):
        t = ('spec', 'template', 'spec', 'containers')
        container = find_container(self.doc, t, 'kube-prometheus-stack')
        out['prometheus-operator'] = container['image']

    def is_reaper(self):
        return self.doc['kind'] == 'Reaper'

    def handle_reaper(self):
        out['reaper'] = self.doc['spec']['image']

    def is_reaper_operator(self):
        return self.doc['kind'] == 'Deployment' and \
            self.doc['metadata']['name'] == f'{app_name}-reaper-operator'

    def handle_reaper_operator(self):
        t = ('spec', 'template', 'spec', 'containers')
        container = find_container(self.doc, t, 'reaper-operator')
        out['reaper-operator'] = container['image']

    def is_stargate(self):
        return self.doc['kind'] == 'Deployment' and \
            self.doc['metadata']['name'] == f'{app_name}-dc1-stargate'

    def handle_stargate(self):
        t = ('spec', 'template', 'spec', 'containers')
        container = find_container(self.doc, t, f'{app_name}-dc1-stargate')
        out['stargate'] = container['image']

    def is_stargate_wait_for_cassandra(self):
        return self.doc['kind'] == 'Deployment' and \
            self.doc['metadata']['name'] == f'{app_name}-dc1-stargate'

    def handle_stargate_wait_for_cassandra(self):
        t = ('spec', 'template', 'spec', 'initContainers')
        container = find_container(self.doc, t, 'wait-for-cassandra')
        out['stargate-wait-for-cassandra'] = container['image']

with open('manifest.yaml') as f:
    y = yaml.safe_load_all(f)

    for doc in iter(y):
        handler = Handler(doc)
        for name in out.keys():
            method_test = f'is_{name}'.replace('-','_')
            method_handle = f'handle_{name}'.replace('-','_')
            if getattr(handler, method_test)():
                getattr(handler, method_handle)()

print(yaml.dump(out))

