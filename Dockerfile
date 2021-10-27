FROM gcr.io/cloud-marketplace-tools/k8s/deployer_helm/onbuild

COPY fixes/files/create_manifests.sh /bin/
COPY fixes/files/deploy.sh /bin/
COPY fixes/files/admission-controller.yaml /app/

RUN /bin/bash -c 'curl -s "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh" | bash; \
mv ./kustomize /bin/'

