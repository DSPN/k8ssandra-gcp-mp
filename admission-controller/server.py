import pprint
import time

from flask import Flask, request, jsonify
from kubernetes import client, config

from logging.config import dictConfig

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

admission_controller = Flask(__name__)

def remove_finalizer(namespace, name):
    config.load_incluster_config()
    custom_api = client.CustomObjectsApi()
    group = "cassandra.datastax.com"
    version = "v1beta1"
    namespace = namespace
    plural = "cassandradatacenters"
    body = {
        "metadata" : {
            "finalizers": None
        }
    }
    api_response = custom_api.patch_namespaced_custom_object(
        group,
        version,
        namespace,
        plural,
        name,
        body
    )

def get_cassandra_datacenters(namespace):
    config.load_incluster_config()
    custom_api = client.CustomObjectsApi()
    group = "cassandra.datastax.com"
    version = "v1beta1"
    namespace = namespace
    plural = "cassandradatacenters"
    api_response = custom_api.list_namespaced_custom_object(
        group,
        version,
        namespace,
        plural
    )
    dcs = []
    for dc in api_response['items']:
        admission_controller.logger.info(pprint.pformat(dc))
        dcs.append(dc['metadata']['name'])
    return dcs

def remove_deployment(deployment, app_name, namespace):
    config.load_incluster_config()
    apps_api = client.AppsV1Api()
    name = "{}-{}".format(app_name, deployment)
    apps_api.delete_namespaced_deployment(name, namespace, grace_period_seconds=0, propagation_policy="Foreground")

def remove_service(service, app_name, namespace):
    config.load_incluster_config()
    core_api = client.CoreV1Api()
    name = "{}-{}".format(app_name, service)
    core_api.delete_namespaced_service(name, namespace, grace_period_seconds=0, propagation_policy="Foreground")

def remove_secret(secret, app_name, namespace):
    config.load_incluster_config()
    core_api = client.CoreV1Api()
    name = "{}-{}".format(app_name, secret)
    core_api.delete_namespaced_secret(name, namespace, grace_period_seconds=0, propagation_policy="Foreground")

@admission_controller.route('/validate/applications', methods=['POST'])
def deployment_webhook():
    try:
        admission_review = request.json
        admission_controller.logger.info(pprint.pformat(admission_review))
        namespace = admission_review['request']['namespace']
        name = admission_review['request']['name']
        uid = admission_review['request']['uid']
        is_application = admission_review.get('request', {}).get('requestKind', {}).get('kind','') == 'Application'
        if not is_application or is_application and admission_review['request']['operation'] != 'DELETE':
            return allow(uid)

        # We need to remove the cass-operator deployment first
        # before we remove the finalizer or it will restore
        # it.
        remove_deployment('cass-operator', name, namespace)
        time.sleep(5)

        cassandra_datacenters = get_cassandra_datacenters(namespace)

        for dc in cassandra_datacenters:
            remove_finalizer(namespace, dc)

        time.sleep(5)

        remove_deployment('admiss-ctrl-datastax', name, namespace)
        remove_service('admiss-ctrl-datastax', name, namespace)
        remove_secret('admiss-ctrl-datastax', name, namespace)

    except Exception as e:
        admission_controller.logger.error(e)

    return allow(uid)

def allow(uid):
    return jsonify({
        "apiVersion": "admission.k8s.io/v1",
        "kind": "AdmissionReview",
        "response" : {"allowed" : True, "status" : {"message" : "n/a"}, "uid" : uid}
    })

if __name__ == '__main__':
    admission_controller.run(
        debug=False,
        host='0.0.0.0',
        port=4443,
        ssl_context=("/admission-controller/cert/tls.crt", "/admission-controller/cert/tls.key")
    )
