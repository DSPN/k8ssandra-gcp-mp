FROM gcr.io/cloud-marketplace-tools/k8s/deployer_helm/onbuild

COPY files/create_manifests.sh /bin/
COPY files/deploy.sh /bin/
COPY files/print_config.py /bin/
COPY files/parse_cassandra_dcs.py /bin/
COPY files/admission-controller.yaml /app/
COPY files/labels_and_service_accounts_kustomize.yaml /app/
COPY files/excluded_resources_kustomize.yaml /app/

RUN /bin/bash -c 'chmod u+x /bin/print_config.py'
RUN /bin/bash -c 'curl -s "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh" | bash; \
mv ./kustomize /bin/'

