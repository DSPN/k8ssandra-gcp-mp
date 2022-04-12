#!/bin/bash
#
# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -eox pipefail

# This is the entry point for the test deployment

# If any command returns with non-zero exit code, set -e will cause the script
# to exit. Prior to exit, set App assembly status to "Failed".
handle_failure() {
  code=$?
  if [[ -z "$NAME" ]] || [[ -z "$NAMESPACE" ]]; then
    # /bin/expand_config.py might have failed.
    # We fall back to the unexpanded params to get the name and namespace.
    NAME="$(/bin/print_config.py \
            --xtype NAME \
            --values_mode raw)"
    NAMESPACE="$(/bin/print_config.py \
            --xtype NAMESPACE \
            --values_mode raw)"
    export NAME
    export NAMESPACE
  fi
  patch_assembly_phase.sh --status="Failed"
  exit $code
}
trap "handle_failure" EXIT

LOG_SMOKE_TEST="SMOKE_TEST"
test_schema="/data-test/schema.yaml"
overlay_test_schema.py \
  --test_schema "$test_schema" \
  --original_schema "/data/schema.yaml" \
  --output "/data/schema.yaml"

NAME="$(/bin/print_config.py \
    --xtype NAME \
    --values_mode raw)"
NAMESPACE="$(/bin/print_config.py \
    --xtype NAMESPACE \
    --values_mode raw)"
export NAME
export NAMESPACE

echo "Deploying application \"$NAME\" in test mode"

app_uid=$(kubectl get "applications.app.k8s.io/$NAME" \
  --namespace="$NAMESPACE" \
  --output=jsonpath='{.metadata.uid}')
app_api_version=$(kubectl get "applications.app.k8s.io/$NAME" \
  --namespace="$NAMESPACE" \
  --output=jsonpath='{.apiVersion}')
namespace_uid=$(kubectl get "namespaces/$NAMESPACE" \
  --output=jsonpath='{.metadata.uid}')

/bin/expand_config.py --values_mode raw --app_uid "$app_uid"

create_manifests.sh --mode="test"

export ADMISS_CTRL_SA="$(get-service-account.sh 'admiss-ctrl-sa')"
export CASS_OPERATOR_SA="$(get-service-account.sh 'cass-operator-sa')"
export WEBHOOK_ADMISS_SA="$(get-service-account.sh 'webhook-admiss-sa')"
export GRAFANA_SA="$(get-service-account.sh 'grafana-sa')"
export PROM_OPERATOR_SA="$(get-service-account.sh 'prom-operator-sa')"
export PROMETHEUS_SA="$(get-service-account.sh 'prometheus-sa')"

export ADMISS_CTRL_DEPLOYMENT="$(/usr/bin/env python3 /app/get-resource-name.py 'admiss-ctrl')"
export CASS_OPERATOR_DEPLOYMENT="$(/usr/bin/env python3 /app/get-resource-name.py 'cass-operator')"
export WEBHOOK_ADMISS_CREATE_JOB="$(/usr/bin/env python3 /app/get-resource-name.py 'admiss-create')"
export WEBHOOK_ADMISS_PATCH_JOB="$(/usr/bin/env python3 /app/get-resource-name.py 'admiss-patch')"
export GRAFANA_DEPLOYMENT="$(/usr/bin/env python3 /app/get-resource-name.py 'grafana')"
export PROM_OPERATOR_DEPLOYMENT="$(/usr/bin/env python3 /app/get-resource-name.py 'prom-operator')"
export PROMETHEUS_DEPLOYMENT="$(/usr/bin/env python3 /app/get-resource-name.py 'prometheus')"
export CASS_OPERATOR_ORIG_SA="$(/usr/bin/env python3 /app/get-resource-name.py 'cass-operator-sa')"

export PROM_NAME="${PROMETHEUS_DEPLOYMENT%%-prometheus}"
echo "$PROM_NAME"

export UBBAGENT_IMAGE="$(grep '^ubbagent-image-repository:' /data/final_values.yaml | awk -F ' ' '{print $2}')"
export REPORTING_SECRET="$(grep '^reportingSecret:' /data/final_values.yaml | awk -F ' ' '{print $2}')"

# Create the medusa gcp key if medusa is enabled
if grep -E "k8ssandra.medusa.enabled.*true" /data/final_values.yaml; then
    medusa_storage_credentials_line=$(grep -E "k8ssandra.medusa.storageCredentialsJSON" /data/final_values.yaml)
    temp=${medusa_storage_credentials_line#*: }
    temp=${temp%\'}
    temp=${temp#\'}
    echo ${temp} > /app/medusa-gcp-key
    kubectl create secret generic prod-k8ssandra-mp-medusa-key --from-file=medusa_gcp_key.json=/app/medusa-gcp-key
fi

envsubst \
    < /app/labels_and_service_accounts_kustomize.yaml \
    > /data/manifest-expanded/kustomization.yaml
kustomize build /data/manifest-expanded > /data/manifest-expanded/chart-kustomized.yaml
mv /data/manifest-expanded/chart-kustomized.yaml /data/manifest-expanded/chart.yaml

envsubst \
    < /app/excluded_resources_kustomize.yaml \
    > /data/manifest-expanded/kustomization.yaml
kustomize build /data/manifest-expanded > /data/manifest-expanded/chart-kustomized.yaml
mv /data/manifest-expanded/chart-kustomized.yaml /data/manifest-expanded/chart.yaml

envsubst \
    < /app/kube-admission-create-kustomize.yaml \
    > /data/manifest-expanded/kustomization.yaml
kustomize build /data/manifest-expanded > /data/manifest-expanded/chart-kustomized.yaml
mv /data/manifest-expanded/chart-kustomized.yaml /data/manifest-expanded/chart.yaml

envsubst \
    < /app/crds_kustomize.yaml \
    > /data/manifest-expanded/kustomization.yaml
kustomize build /data/manifest-expanded > /data/manifest-expanded/chart-kustomized.yaml
mv /data/manifest-expanded/chart-kustomized.yaml /data/manifest-expanded/chart.yaml

envsubst \
    < /app/billing-agent-kustomize.yaml \
    > /data/manifest-expanded/kustomization.yaml
kustomize build /data/manifest-expanded > /data/manifest-expanded/chart-kustomized.yaml
mv /data/manifest-expanded/chart-kustomized.yaml /data/manifest-expanded/chart.yaml

rm /data/manifest-expanded/kustomization.yaml

# Remove unneeded version strings in the chart template
sed -i 's|^  version: 1.3.*$||' /data/manifest-expanded/chart.yaml
sed -i 's|^ *app.kubernetes.io/version: 1.3.*$||g' /data/manifest-expanded/chart.yaml

/usr/bin/env python3 /app/remove-cass-crd.py

# Add admission-controller resources
openssl req -x509 \
    -sha256 \
    -newkey rsa:2048 \
    -keyout /app/tls.key \
    -out /app/tls.crt \
    -days 18250 \
    -nodes \
    -subj "/C=US/ST=CA/L=NA/O=IT/CN=$NAME-admiss-ctrl-datastax.$NAMESPACE.svc"
cat /app/tls.key | base64 -w 0 > /app/tlsb64e.key
cat /app/tls.crt | base64 -w 0 > /app/tlsb64e.crt

# Assign owner references for the resources.
/bin/set_ownership.py \
  --app_name "$NAME" \
  --app_uid "$app_uid" \
  --app_api_version "$app_api_version" \
  --namespace "$NAMESPACE" \
  --namespace_uid "$namespace_uid" \
  --manifests "/data/manifest-expanded" \
  --dest "/data/resources.yaml"

validate_app_resource.py --manifests "/data/resources.yaml"

separate_tester_resources.py \
  --app_uid "$app_uid" \
  --app_name "$NAME" \
  --app_api_version "$app_api_version" \
  --manifests "/data/resources.yaml" \
  --out_manifests "/data/resources.yaml" \
  --out_test_manifests "/data/tester.yaml"

# Apply the manifest.
kubectl apply --namespace="$NAMESPACE" \
              --filename="/data/resources.yaml" \
              --selector is-crd=yes || true
kubectl apply --namespace="$NAMESPACE" \
              --filename="/app/cassandra-datacenter-crd.yaml"

# wait for CRDS to be created.
# TODO: use something like kubectl wait --for condition=established --timeout=120s instead of hard coding a timeout here.
sleep 30

# Apply a second time due to: https://github.com/kubernetes/kubectl/issues/1117
kubectl apply --namespace="$NAMESPACE" \
              --filename="/data/resources.yaml" \
              --selector is-crd=yes || true
kubectl apply --namespace="$NAMESPACE" \
              --filename="/app/cassandra-datacenter-crd.yaml"

# Give enough time for the crds to become available.
sleep 10

# Now apply the other non crd resources.
kubectl apply  --namespace="$NAMESPACE" \
               --filename="/data/resources.yaml" \
               --selector is-crd=no,excluded-resource=no

sleep 10
admission_controller_deployment_uid=$(kubectl get "deployments/$ADMISS_CTRL_DEPLOYMENT" \
  --namespace="$NAMESPACE" \
  --output=jsonpath='{.metadata.uid}')

sed -i "s|ADMISSION_CONTROLLER_DATASTAX_DEPLOYMENT_UID|$admission_controller_deployment_uid|g" /data/resources.yaml
kubectl apply --namespace="$NAMESPACE" \
              --filename="/data/resources.yaml" \
              --selector k8ssandra-mp-component=admiss-ctrl-datastax

kubectl patch --namespace="$NAMESPACE" secret ${NAME}-admiss-ctrl-datastax --type=json --patch-file=/dev/stdin <<-EOF
[
  {
    "op": "replace",
    "path": "/data/tls.crt",
    "value": "$(cat /app/tlsb64e.crt)"
  },
  {
    "op": "replace",
    "path": "/data/tls.key",
    "value": "$(cat /app/tlsb64e.key)"
  }
]
EOF
kubectl patch --namespace="$NAMESPACE" secret ${NAME}-admiss-ctrl-datastax --type=json --patch-file=/dev/stdin <<-EOF
[
  {
    "op": "remove",
    "path": "/metadata/ownerReferences/1"
  }
]
EOF
kubectl patch --namespace="$NAMESPACE" service ${NAME}-admiss-ctrl-datastax --type=json --patch-file=/dev/stdin <<-EOF
[
  {
    "op": "remove",
    "path": "/metadata/ownerReferences/1"
  }
]
EOF

kubectl get --namespace="$NAMESPACE" validatingwebhookconfiguration ${NAME}-admiss-ctrl-datastax -o yaml > /app/vwc.yaml
sed -r -i "s|(^ *?caBundle:).*$|\1 $(cat /app/tlsb64e.crt)|" /app/vwc.yaml
kubectl apply --namespace="$NAMESPACE" -f /app/vwc.yaml

# restart the admission controller deployment so the secret containing the
# new tls certs will take affect.
kubectl rollout --namespace="$NAMESPACE" restart deployment $ADMISS_CTRL_DEPLOYMENT

patch_assembly_phase.sh --status="Success"

wait_for_ready.py \
  --name $NAME \
  --namespace $NAMESPACE \
  --timeout ${WAIT_FOR_READY_TIMEOUT:-1500}

tester_manifest="/data/tester.yaml"
if [[ -e "$tester_manifest" ]]; then
  cat $tester_manifest

  run_tester.py \
    --namespace $NAMESPACE \
    --manifest $tester_manifest \
    --timeout ${TESTER_TIMEOUT:-300}
else
  echo "$LOG_SMOKE_TEST No tester manifest found at $tester_manifest."
fi

clean_iam_resources.sh

trap - EXIT
