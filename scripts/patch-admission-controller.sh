#!/bin/bash

set -eox pipefail

work_dir="$(mktemp -d)"

on_exit() {

    code=$?

    if [ -d "${work_dir}" ]; then
        (
            cd "${work_dir}" && rm -rf *
        )
        rmdir "${work_dir}"
    fi

  exit ${code}
}

trap "on_exit" EXIT

app_instance_name="$1"

if [ -z "${app_instance_name}" ]; then
    echo "app_instance_name is required"
    exit 1
fi

script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd "${work_dir}"

export ADMISS_CTRL_DEPLOYMENT="${app_instance_name}-admiss-ctrl-datastax"

# Add admission-controller resources
openssl req -x509 \
    -sha256 \
    -newkey rsa:2048 \
    -keyout tls.key \
    -out tls.crt \
    -days 18250 \
    -nodes \
    -subj "/C=US/ST=CA/L=NA/O=IT/CN=${app_instance_name}-admiss-ctrl-datastax.$NAMESPACE.svc"
b64arg="-w 0"
if base64 --help | grep -- "-b"; then
    b64arg="-b 0"
fi
cat ./tls.key | base64 "${b64arg}" > ./tlsb64e.key
cat ./tls.crt | base64 "${b64arg}" > ./tlsb64e.crt

admission_controller_deployment_uid=$(kubectl get "deployments/$ADMISS_CTRL_DEPLOYMENT" \
  --namespace="$NAMESPACE" \
  --output=jsonpath='{.metadata.uid}')

sed -i "s|ADMISSION_CONTROLLER_DATASTAX_DEPLOYMENT_UID|$admission_controller_deployment_uid|g" "${script_dir}/../${app_instance_name}_manifest.yaml"
kubectl apply --namespace="$NAMESPACE" \
              --filename="${script_dir}/../${app_instance_name}_manifest.yaml" \
              --selector k8ssandra-mp-component=admiss-ctrl-datastax

kubectl patch --namespace="$NAMESPACE" secret ${app_instance_name}-admiss-ctrl-datastax --type=json --patch-file=/dev/stdin <<-EOF
[
  {
    "op": "replace",
    "path": "/data/tls.crt",
    "value": "$(cat ./tlsb64e.crt)"
  },
  {
    "op": "replace",
    "path": "/data/tls.key",
    "value": "$(cat ./tlsb64e.key)"
  }
]
EOF

kubectl get --namespace="$NAMESPACE" validatingwebhookconfiguration ${app_instance_name}-admiss-ctrl-datastax -o yaml > /app/vwc.yaml
sed -r -i "s|(^ *?caBundle:).*$|\1 $(cat ./tlsb64e.crt)|" ./vwc.yaml
kubectl apply --namespace="$NAMESPACE" -f ./vwc.yaml

# restart the admission controller deployment so the secret containing the
# new tls certs will take affect.
kubectl rollout --namespace="$NAMESPACE" restart deployment $ADMISS_CTRL_DEPLOYMENT

