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
chart_file_name="${app_instance_name}_manifest.yaml"

cd "${work_dir}"

cp "${script_dir}"/../"${app_instance_name}_manifest.yaml" ./chart.yaml

export CASS_OPERATOR_SA="${app_instance_name}-cass-operator-sa"
export WEBHOOK_ADMISS_SA="${app_instance_name}-webhook-admiss-sa"
export GRAFANA_SA="${app_instance_name}-grafana-sa"
export PROM_OPERATOR_SA="${app_instance_name}-prom-operator-sa"
export PROMETHEUS_SA="${app_instance_name}-prometheus-sa"

export CASS_OPERATOR_DEPLOYMENT="${app_instance_name}-cass-operator"
export WEBHOOK_ADMISS_CREATE_JOB="${app_instance_name}-prom-admission-create"
export WEBHOOK_ADMISS_PATCH_JOB="${app_instance_name}-prom-admission-patch"
export GRAFANA_DEPLOYMENT="${app_instance_name}-grafana"
export PROM_OPERATOR_DEPLOYMENT="${app_instance_name}-prom-operator"
export PROMETHEUS_DEPLOYMENT="${app_instance_name}-prom-prometheus"
export CASS_OPERATOR_ORIG_SA="${app_instance_name}-cass-operator"

export PROM_NAME="${PROMETHEUS_DEPLOYMENT%%-prometheus}"
echo "$PROM_NAME"

# Apply labels and service account modifications

NAME="${app_instance_name}" envsubst \
    < "${script_dir}"/../files/labels_and_service_accounts_kustomize.yaml \
    > ./kustomization.yaml
kustomize build . > ./chart-kustomized.yaml
mv ./chart-kustomized.yaml ./chart.yaml

# Apply excluded resources modifications

NAME="${app_instance_name}" envsubst \
    < "${script_dir}"/../files/excluded_resources_kustomize.yaml \
    > ./kustomization.yaml
kustomize build . > ./chart-kustomized.yaml
mv ./chart-kustomized.yaml ./chart.yaml

# Apply CRD designation to all of the CRDS

NAME="${app_instance_name}" envsubst \
    < "${script_dir}"/../files/crds_kustomize.yaml \
    > ./kustomization.yaml
kustomize build . > ./chart-kustomized.yaml
mv ./chart-kustomized.yaml ./chart.yaml

# Apply usage based billing agent modifications
NAME="${app_instance_name}" envsubst \
    < "${script_dir}"/../files/billing-agent-kustomize.yaml \
    > ./kustomization.yaml
kustomize build . > ./chart-kustomized.yaml

mv ./chart-kustomized.yaml "${script_dir}"/../"${chart_file_name}"

# Remove unneeded version strings

sed -i'' 's|^ *version: 1\.3$||g' "${script_dir}"/../"${chart_file_name}"
sed -i'' 's|^ *app.kubernetes\.io/version: "1\.3".*$||g' "${script_dir}"/../"${chart_file_name}"

