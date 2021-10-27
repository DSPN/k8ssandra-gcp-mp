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

def remove_cass_operator_deployment(app_name, namespace):
    config.load_incluster_config()
    apps_api = client.AppsV1Api()
    name = "{}-cass-operator".format(app_name, namespace)
    apps_api.delete_namespaced_deployment(name, namespace, propagation_policy="Background")

def remove_admission_controller_deployment(app_name, namespace):
    config.load_incluster_config()
    apps_api = client.AppsV1Api()
    name = "{}-admission-controller-datastax".format(app_name, namespace)
    apps_api.delete_namespaced_deployment(name, namespace, propagation_policy="Background")

@admission_controller.route('/validate/applications', methods=['POST'])
def deployment_webhook():
    try:
        admission_review = request.json
        admission_controller.logger.info(pprint.pformat(admission_review))
        namespace = admission_review['request']['namespace']
        name = admission_review['request']['name']
        uid = admission_review['request']['uid']

        # We need to remove the cass-operator deployment first
        # before we remove the finalizer or it will restore
        # it.
        remove_cass_operator_deployment(name, namespace)
        time.sleep(5)

        cassandra_datacenters = get_cassandra_datacenters(namespace)

        for dc in cassandra_datacenters:
            remove_finalizer(namespace, dc)

        time.sleep(5)
        remove_admission_controller_deployment(name, namespace)
    except Exception as e:
        admission_controller.logger.error(e)

    return jsonify({
        "response" : {"allowed" : True, "status" : {"message" : "success"}, "uid" : uid}
    })

if __name__ == '__main__':
    admission_controller.run(
        debug=True,
        host='0.0.0.0',
        port=4443,
        ssl_context=("/admission-controller/cert/tls.crt", "/admission-controller/cert/tls.key")
    )
