FROM gcr.io/cloud-marketplace-tools/k8s/deployer_helm/onbuild

COPY fixes/files/create_manifests.sh /bin/

