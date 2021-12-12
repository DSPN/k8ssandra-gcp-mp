import os
import subprocess

import yaml

valid_versions = [
    "1.4.1"
]

dev_staging_repo = "gcr.io/gke-launcher-dev/k8ssandra-mp"
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
