import os
import subprocess

import yaml

valid_versions = [
    "1.3.1"
]

application_name = 'k8ssandra-mp'
dev_staging_repo = f"gcr.io/gke-launcher-dev/{application_name}"
prod_staging_repo = f"gcr.io/datastax-public/{application_name}"
tools_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))

def run(command):
    cp = subprocess.run(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding='utf-8')

    return cp

def get_versions():
    doc = yaml.safe_load(open(f"{tools_dir}/../chart/k8ssandra-mp/Chart.yaml"))
    version = doc['version']
    if version not in valid_versions:
        raise Exception(f"invalid version found in Chart.yaml: '{version}'")
    short_version = get_short_version(version)
    return (version, short_version)

def get_short_version(version):
    return '.'.join(version.split('.')[0:2])

def render_template(include_crds=False):
    include_crds_opt = '--include-crds' if include_crds else ""
    cp = run(
        f"""
        helm template k8ssandra-mp {tools_dir}/../chart/k8ssandra-mp \
            {include_crds_opt} \
            --set k8ssandra.reaper.enabled=true \
            --set k8ssandra.reaper-operator.enabled=true \
            --set k8ssandra.stargate.enabled=true \
            --set k8ssandra.kube-prometheus-stack.enabled=true \
            --set k8ssandra.medusa.enabled=true
        """
        )
    if cp.returncode != 0:
        raise Exception(
            f"""
            Failed to render chart template:
            {cp.stdout}
            """
            )

    return cp.stdout
