FROM gcr.io/cloud-marketplace-tools/k8s/deployer_helm/onbuild

COPY files/create_manifests.sh /bin/
COPY files/deploy.sh /bin/
COPY files/deploy_with_tests.sh /bin/
COPY files/print_config.py /bin/
COPY files/parse_cassandra_dcs.py /bin/
COPY files/get-service-account.sh /bin/
COPY files/labels_and_service_accounts_kustomize.yaml /app/
COPY files/excluded_resources_kustomize.yaml /app/
COPY files/crds_kustomize.yaml /app/
COPY files/kube-admission-create-kustomize.yaml /app/
COPY files/billing-agent-kustomize.yaml /app/
COPY files/cassandra-datacenter-crd.yaml /app/
COPY files/remove-cass-crd.py /app/
COPY files/get-resource-name.py /app/

COPY 3rd-party /3rd-party

RUN wget https://github.com/qos-ch/logback/archive/refs/tags/v_1.2.3.tar.gz &&\
    tar xzvf v_1.2.3.tar.gz &&\
    mv logback-v_1.2.3 /3rd-party/vendor/github.com/qos-ch/logback@v1.2.3 &&\
    rm v_1.2.3.tar.gz

RUN /bin/bash -c 'chmod u+x /bin/print_config.py'
RUN /bin/bash -c 'chmod u+x /bin/get-service-account.sh'
RUN /bin/bash -c 'curl -s "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh" | bash; \
mv ./kustomize /bin/'

ENV WAIT_FOR_READY_TIMEOUT 1500 
ENV TESTER_TIMEOUT 1500
