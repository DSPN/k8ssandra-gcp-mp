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

cp "${script_dir}"/../"${app_instance_name}_manifest.yaml" .

# Apply labels and service account modifications

CHART_FILE_NAME="${chart_file_name}" NAME="${app_instance_name}" envsubst \
    < "${script_dir}"/../files/labels_and_service_accounts_kustomize.yaml \
    > ./kustomization.yaml
kustomize build . > ./chart-kustomized.yaml

# Apply excluded resources modifications

CHART_FILE_NAME=chart-kustomized.yaml NAME="${app_instance_name}" envsubst \
    < "${script_dir}"/../files/excluded_resources_kustomize.yaml \
    > ./kustomization.yaml
kustomize build . > "${script_dir}"/../"${chart_file_name}"

