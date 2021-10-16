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

# This is the entry point for the production deployment

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

NAME="$(/bin/print_config.py \
    --xtype NAME \
    --values_mode raw)"
NAMESPACE="$(/bin/print_config.py \
    --xtype NAMESPACE \
    --values_mode raw)"
export NAME
export NAMESPACE

echo "Deploying application \"$NAME\""

app_uid=$(kubectl get "applications.app.k8s.io/$NAME" \
  --namespace="$NAMESPACE" \
  --output=jsonpath='{.metadata.uid}')
app_api_version=$(kubectl get "applications.app.k8s.io/$NAME" \
  --namespace="$NAMESPACE" \
  --output=jsonpath='{.apiVersion}')

/bin/expand_config.py --values_mode raw --app_uid "$app_uid"

create_manifests.sh

cat > /data/manifest-expanded/kustomization.yaml <<EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
commonLabels:
  app.kubernetes.io/name: $NAME
  excluded-resource: "no"

patches:
  - patch: |-
      - op: replace
        path: /spec/template/spec/serviceAccountName
        value: "$NAME-grafanaserviceaccount"
    target:
      kind: Deployment
      name: "$NAME-grafana"
  - patch: |-
      - op: replace
        path: /spec/template/spec/serviceAccountName
        value: "$NAME-cass-operatorserviceaccount"
    target:
      kind: Deployment
      name: "$NAME-cass-operator"
  - patch: |-
      - op: replace
        path: /spec/template/spec/serviceAccountName
        value: "$NAME-kube-promethe-admissionserviceaccount"
    target:
      kind: Job
      name: "$NAME-kube-promethe-admission-create"
  - patch: |-
      - op: replace
        path: /spec/template/spec/serviceAccountName
        value: "$NAME-kube-promethe-admissionserviceaccount"
    target:
      kind: Job
      name: "$NAME-kube-promethe-admission-patch"
  - patch: |-
      - op: replace
        path: /spec/template/spec/serviceAccountName
        value: "$NAME-kube-promethe-operatorserviceaccount"
    target:
      kind: Deployment
      name: "$NAME-kube-promethe-operator"
  - patch: |-
      - op: replace
        path: /spec/serviceAccountName
        value: "$NAME-kube-promethe-prometheusserviceaccount"
    target:
      kind: Prometheus
      name: "$NAME-kube-promethe-prometheus"
 
resources:
  - chart.yaml
EOF
kustomize build /data/manifest-expanded > /data/manifest-expanded/chart-kustomized.yaml

cat > /data/manifest-expanded/kustomization.yaml <<EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

patches:
  - patch: |-
      - op: replace
        path: /metadata/labels/excluded-resource
        value: "yes"
    target:
      kind: ServiceAccount
      name: $NAME-grafana
  - patch: |-
      - op: replace
        path: /metadata/labels/excluded-resource
        value: "yes"
    target:
      kind: Role
      name: $NAME-grafana
  - patch: |-
      - op: replace
        path: /metadata/labels/excluded-resource
        value: "yes"
    target:
      kind: RoleBinding
      name: $NAME-grafana
  - patch: |-
      - op: replace
        path: /metadata/labels/excluded-resource
        value: "yes"
    target:
      kind: ClusterRole
      name: $NAME-grafana-clusterrole
  - patch: |-
      - op: replace
        path: /metadata/labels/excluded-resource
        value: "yes"
    target:
      kind: ClusterRoleBinding
      name: $NAME-grafana-clusterrolebinding
  - patch: |-
      - op: replace
        path: /metadata/labels/excluded-resource
        value: "yes"
    target:
      name: $NAME-grafana-test
  - patch: |-
      - op: replace
        path: /metadata/labels/excluded-resource
        value: "yes"
    target:
      kind: ServiceAccount
      name: $NAME-cass-operator
  - patch: |-
      - op: replace
        path: /metadata/labels/excluded-resource
        value: "yes"
    target:
      kind: Role
      name: $NAME-cass-operator
  - patch: |-
      - op: replace
        path: /metadata/labels/excluded-resource
        value: "yes"
    target:
      kind: RoleBinding
      name: $NAME-cass-operator
  - patch: |-
      - op: replace
        path: /metadata/labels/excluded-resource
        value: "yes"
    target:
      kind: ClusterRole
      name: $NAME-cass-operator-cr
  - patch: |-
      - op: replace
        path: /metadata/labels/excluded-resource
        value: "yes"
    target:
      kind: ClusterRoleBinding
      name: $NAME-cass-operator-cr
  - patch: |-
      - op: replace
        path: /metadata/labels/excluded-resource
        value: "yes"
    target:
      kind: ServiceAccount
      name: $NAME-kube-promethe-admission
  - patch: |-
      - op: replace
        path: /metadata/labels/excluded-resource
        value: "yes"
    target:
      kind: Role
      name: $NAME-kube-promethe-admission
  - patch: |-
      - op: replace
        path: /metadata/labels/excluded-resource
        value: "yes"
    target:
      kind: RoleBinding
      name: $NAME-kube-promethe-admission
  - patch: |-
      - op: replace
        path: /metadata/labels/excluded-resource
        value: "yes"
    target:
      kind: ClusterRole
      name: $NAME-kube-promethe-admission
  - patch: |-
      - op: replace
        path: /metadata/labels/excluded-resource
        value: "yes"
    target:
      kind: ClusterRoleBinding
      name: $NAME-kube-promethe-admission
  - patch: |-
      - op: replace
        path: /metadata/labels/excluded-resource
        value: "yes"
    target:
      kind: ServiceAccount
      name: $NAME-kube-promethe-operator
  - patch: |-
      - op: replace
        path: /metadata/labels/excluded-resource
        value: "yes"
    target:
      kind: ClusterRole
      name: $NAME-kube-promethe-operator
  - patch: |-
      - op: replace
        path: /metadata/labels/excluded-resource
        value: "yes"
    target:
      kind: ClusterRoleBinding
      name: $NAME-kube-promethe-operator
  - patch: |-
      - op: replace
        path: /metadata/labels/excluded-resource
        value: "yes"
    target:
      kind: ClusterRole
      name: $NAME-kube-promethe-operator-psp
  - patch: |-
      - op: replace
        path: /metadata/labels/excluded-resource
        value: "yes"
    target:
      kind: ClusterRoleBinding
      name: $NAME-kube-promethe-operator-psp
  - patch: |-
      - op: replace
        path: /metadata/labels/excluded-resource
        value: "yes"
    target:
      kind: ServiceAccount
      name: $NAME-kube-promethe-prometheus
  - patch: |-
      - op: replace
        path: /metadata/labels/excluded-resource
        value: "yes"
    target:
      kind: ClusterRole
      name: $NAME-kube-promethe-prometheus
  - patch: |-
      - op: replace
        path: /metadata/labels/excluded-resource
        value: "yes"
    target:
      kind: ClusterRoleBinding
      name: $NAME-kube-promethe-prometheus
  - patch: |-
      - op: replace
        path: /metadata/labels/excluded-resource
        value: "yes"
    target:
      kind: ClusterRole
      name: $NAME-kube-promethe-prometheus-psp
  - patch: |-
      - op: replace
        path: /metadata/labels/excluded-resource
        value: "yes"
    target:
      kind: ClusterRoleBinding
      name: $NAME-kube-promethe-prometheus-psp
  - patch: |-
      - op: replace
        path: /metadata/labels/excluded-resource
        value: "yes"
    target:
      name: $NAME-cleaner-k8ssandra
  - patch: |-
      - op: replace
        path: /metadata/labels/excluded-resource
        value: "yes"
    target:
      name: $NAME-cleaner-job-k8ssandra
  - patch: |-
      - op: replace
        path: /metadata/labels/excluded-resource
        value: "yes"
    target:
      name: $NAME-crd-upgrader-k8ssandra
  - patch: |-
      - op: replace
        path: /metadata/labels/excluded-resource
        value: "yes"
    target:
      name: $NAME-crd-upgrader-job-k8ssandra

resources:
  - chart-kustomized.yaml
EOF
kustomize build /data/manifest-expanded > /data/manifest-expanded/chart-kustomized2.yaml

mv /data/manifest-expanded/chart-kustomized2.yaml /data/manifest-expanded/chart.yaml
rm /data/manifest-expanded/kustomization.yaml
rm /data/manifest-expanded/chart-kustomized.yaml

# Assign owner references for the resources.
/bin/set_ownership.py \
  --app_name "$NAME" \
  --app_uid "$app_uid" \
  --app_api_version "$app_api_version" \
  --manifests "/data/manifest-expanded" \
  --dest "/data/resources.yaml"

cat /data/resources.yaml

validate_app_resource.py --manifests "/data/resources.yaml"


# Ensure assembly phase is "Pending", until successful kubectl apply.
/bin/setassemblyphase.py \
  --manifest "/data/resources.yaml" \
  --status "Pending"

# Apply the manifest.
kubectl apply --namespace="$NAMESPACE" --filename="/data/resources.yaml" -l excluded-resource=no || true

# wait for CRDS to be created.
# TODO: use something like kubectl wait --for condition=established --timeout=120s instead of hard coding a timeout here.
sleep 60

# Apply a second time due to: https://github.com/kubernetes/kubectl/issues/1117
kubectl apply --namespace="$NAMESPACE" --filename="/data/resources.yaml" -l excluded-resource=no

patch_assembly_phase.sh --status="Success"

clean_iam_resources.sh

trap - EXIT
