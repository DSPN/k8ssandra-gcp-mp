# Overview
Built on the rock-solid Apache Cassandra® NoSQL database, K8ssandra brings together a complete operational data platform for Kubernetes including APIs, monitoring, and backups.

# Installation

## Quick install with Google Cloud Marketplace
Get up and running with a few clicks! Install the k8ssandra marketplace app to a Google Kubernetes Engine cluster by using Google Cloud Marketplace. Follow the [[on-screen-instructions]](https://google.com)

## Command-line instructions
You can use [Google Cloud Shell] or a local workstation to follow the steps below.

### Prerequisites

#### Set up command-line tools

You'll need the following tools in your development environment. If you are using Cloud Shell, these are all installed in your environment by default.

* [gcloud](https://cloud.google.com/sdk/gcloud/)
* [kubectl](https://kubernetes.io/docs/reference/kubectl/overview/)
* [docker](https://docs.docker.com/install/)
* [git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
* [helm](https://helm.sh/)
* [kustomize](https://kustomize.io/)

Configure gcloud as a docker credential helper:

```bash
gcloud auth configure-docker
```

#### Create a Google Kubernetes Engine cluster

Create a new cluster from the command line:

```bash
export CLUSTER=k8ssandra-mp-cluster
export ZONE=us-central1-a
gcloud container clusters create "${CLUSTER}" --zone "$ZONE" --machine-type e2-standard-2
```

Configure kubectl to connect to the cluster:

```bash
gcloud container clusters get-credentials "${CLUSTER}" --zone "${ZONE}"
```

#### Clone this repo

```bash
git clone https://github.com/DSPN/k8ssandra-gcp-mp.git
```

#### Install the Application resource definition

An Application resource is a collection of individual Kubernetes components, such as Services, Deployments, and so on, that you can manage as a group.

To set up your cluster to understand Application resources, run the following command:

```bash
kubectl apply -f "https://raw.githubusercontent.com/GoogleCloudPlatform/marketplace-k8s-app-tools/master/crd/app-crd.yaml"
```

You need to run this command once.

The Application resource is defined by the [Kubernetes SIG-apps](https://github.com/kubernetes/community/tree/master/sig-apps) community. The source code can be found on [github.com/kubernetes-sigs/application](https://github.com/kubernetes-sigs/application).

### Install the Application

#### Navigate to the k8ssandra-gcp-mp directory

```bash
cd k8ssandra-gcp-mp
```

#### Download the k8ssandra charts

```bash
helm repo add k8ssandra https://helm.k8ssandra.io/stable
helm dependency build chart/k8ssandra-mp
```

#### Configure the app with environment variables

Choose an instance name, namespace, and default storage class for the app. In most cases you can use the `default` namespace.

```bash
export APP_INSTANCE_NAME=k8ssandra-mp
export NAMESPACE=default
export DEFAULT_STORAGE_CLASS=k8ssandra-storage
```

Set up the image registry, repository, and tag:

```bash
export REGISTRY="gcr.io"
export REPOSITORY="gke-launcher-dev/k8ssandra-mp"
export TAG="1.0"
```

Configure the container images:

```bash
export IMAGE_BUSY_BOX="busybox"
export IMAGE_CASS_OPERATOR="cass-operator"
export IMAGE_CASSANDRA="cassandra"
export IMAGE_CASSANDRA_CONFIG_BUILDER="cassconfigbuilder"
export IMAGE_CLEANER="cleaner"
export IMAGE_CLIENT="client"
export IMAGE_GRAFANA="grafana"
export IMAGE_GRAFANA_IMAGE_RENDERER="grafanaimagerenderer"
export IMAGE_GRAFANA_SIDECAR="grafanasidecar"
export IMAGE_INIT_CHOWN_DATA="initchowndata"
export IMAGE_JMX_CREDENTIALS_CONFIG="jmxcredentialsconfig"
export IMAGE_LOGGING_SIDECAR="loggingsidecar"
export IMAGE_MEDUSA="medusa"
export IMAGE_MEDUSA_OPERATOR="medusaoperator"
export IMAGE_PROMETHEUS_OPERATOR="prometheusoperator"
export IMAGE_PROMETHEUS_SPEC="prometheusspec"
export IMAGE_REAPER="reaper"
export IMAGE_REAPER_OPERATOR="reaperoperator"
export IMAGE_STARGATE="stargate"
export IMAGE_WAIT_FOR_CASSANDRA="waitforcassandra"
```

#### Create a suitable storage class

Create a storage class that will be used by the Cassandra persistent storage volume claims:

```bash
cat <<EOF | kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ${DEFAULT_STORAGE_CLASS}
provisioner: kubernetes.io/gce-pd
parameters:
  type: pd-standard
  fstype: ext4
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
EOF
```

#### Create the namespace in your Kubernetes cluster

If you use a namespace other than the `default`, run the command below to create a new namespace.

```bash
kubectl create namespace "${NAMESPACE}"
```

#### Create service accounts and RBAC resources for each of the k8ssandra components

##### grafana

```bash
#service account:
kubectl create serviceaccount "${APP_INSTANCE_NAME}-grafanaserviceaccount" \
    --namespace="${NAMESPACE}"
kubectl label serviceaccounts "${APP_INSTANCE_NAME}-grafanaserviceaccount" app.kubernetes.io/name="${APP_INSTANCE_NAME}" \
    --namespace="${NAMESPACE}"

#role:
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  labels:
    app.kubernetes.io/name: ${NAMESPACE}
  name: ${APP_INSTANCE_NAME}:grafanaServiceAccount
  namespace: ${NAMESPACE}
rules:
- apiGroups:
  - extensions
  - ""
  resources:
  - podsecuritypolicies
  - secrets
  - configmaps
  verbs:
  - use
  - get
  - list
  - watch
EOF

#rolebinding:
kubectl create rolebinding "${APP_INSTANCE_NAME}:grafanaServiceAccount" \
    --namespace="${NAMESPACE}" \
    --role="${APP_INSTANCE_NAME}:grafanaServiceAccount" \
    --serviceaccount="${NAMESPACE}:${APP_INSTANCE_NAME}-grafanaserviceaccount"
kubectl label rolebindings "${APP_INSTANCE_NAME}:grafanaServiceAccount" app.kubernetes.io/name="${APP_INSTANCE_NAME}" \
    --namespace="${NAMESPACE}"
```

##### cass-operator

```bash
#service account:
kubectl create serviceaccount "${APP_INSTANCE_NAME}-cass-operatorserviceaccount" \
    --namespace="${NAMESPACE}"
kubectl label serviceaccounts "${APP_INSTANCE_NAME}-cass-operatorserviceaccount" app.kubernetes.io/name="${APP_INSTANCE_NAME}" \
    --namespace="${NAMESPACE}"

#role:
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  labels:
    app.kubernetes.io/name: ${APP_INSTANCE_NAME}
  name: "${APP_INSTANCE_NAME}:cass-operatorServiceAccount"
  namespace: "${NAMESPACE}"
rules:
- apiGroups:
  - ""
  resources:
  - pods
  - services
  - endpoints
  - persistentvolumeclaims
  - events
  - configmaps
  - secrets
  verbs:
  - '*'
- apiGroups:
  - ""
  resources:
  - namespaces
  verbs:
  - get
- apiGroups:
  - apps
  resources:
  - deployments
  - daemonsets
  - replicasets
  - statefulsets
  verbs:
  - '*'
- apiGroups:
  - monitoring.coreos.com
  resources:
  - servicemonitors
  verbs:
  - get
  - create
- apiGroups:
  - apps
  resources:
  - deployments/finalizers
  verbs:
  - update
- apiGroups:
  - datastax.com
  resources:
  - '*'
  verbs:
  - '*'
- apiGroups:
  - policy
  resources:
  - poddisruptionbudgets
  verbs:
  - '*'
- apiGroups:
  - cassandra.datastax.com
  resources:
  - '*'
  verbs:
  - '*'
- apiGroups:
  - batch
  resources:
  - '*'
  verbs:
  - '*'
EOF

# rolebinding:
kubectl create rolebinding "${APP_INSTANCE_NAME}:cass-operatorServiceAccount" \
    --namespace="${NAMESPACE}" \
    --role="${APP_INSTANCE_NAME}:cass-operatorServiceAccount" \
    --serviceaccount="${NAMESPACE}:${APP_INSTANCE_NAME}-cass-operatorserviceaccount"
kubectl label rolebindings "${APP_INSTANCE_NAME}:cass-operatorServiceAccount" app.kubernetes.io/name="${APP_INSTANCE_NAME}" \
    --namespace="${NAMESPACE}"

# clusterrole:
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  labels:
    app.kubernetes.io/name: ${APP_INSTANCE_NAME}
  name: "${APP_INSTANCE_NAME}:cass-operatorServiceAccount"
rules:
- apiGroups:
  - ""
  resources:
  - nodes 
  - persistentvolumes
  verbs:
  - get
  - watch
  - list
EOF

# clusterrolebinding:
kubectl create clusterrolebinding "${APP_INSTANCE_NAME}:cass-operatorServiceAccount" \
    --namespace="${NAMESPACE}" \
    --clusterrole="${APP_INSTANCE_NAME}:cass-operatorServiceAccount" \
    --serviceaccount="${NAMESPACE}:${APP_INSTANCE_NAME}-cass-operatorserviceaccount"
kubectl label clusterrolebindings "${APP_INSTANCE_NAME}:cass-operatorServiceAccount" app.kubernetes.io/name="${APP_INSTANCE_NAME}" \
    --namespace="${NAMESPACE}"
```

##### kube-promethe-admission

```bash
# service account:
kubectl create serviceaccount "${APP_INSTANCE_NAME}-kube-promethe-admissionserviceaccount" \
    --namespace="${NAMESPACE}"
kubectl label serviceaccounts "${APP_INSTANCE_NAME}-kube-promethe-admissionserviceaccount" app.kubernetes.io/name="${APP_INSTANCE_NAME}" \
    --namespace="${NAMESPACE}"

# role:
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  labels:
    app.kubernetes.io/name: ${APP_INSTANCE_NAME}
  name: ${APP_INSTANCE_NAME}:kube-promethe-admissionServiceAccount
  namespace: ${NAMESPACE}
rules:
- apiGroups:
  - ""
  resources:
  - secrets
  verbs:
  - get
  - create
EOF

# rolebinding:
kubectl create rolebinding "${APP_INSTANCE_NAME}:kube-promethe-admissionServiceAccount" \
    --namespace="${NAMESPACE}" \
    --role="${APP_INSTANCE_NAME}:kube-promethe-admissionServiceAccount" \
    --serviceaccount="${NAMESPACE}:${APP_INSTANCE_NAME}-kube-promethe-admissionserviceaccount"
kubectl label rolebindings "${APP_INSTANCE_NAME}:kube-promethe-admissionServiceAccount" app.kubernetes.io/name="${APP_INSTANCE_NAME}" \
    --namespace="${NAMESPACE}"

# clusterrole:
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  labels:
    app.kubernetes.io/name: ${APP_INSTANCE_NAME}
    app.kubernetes.io/namespace: "${NAMESPACE}"
  name: ${NAMESPACE}:${APP_INSTANCE_NAME}:kube-promethe-admissionServiceAccount
rules:
- apiGroups:
  - admissionregistration.k8s.io
  resources:
  - validatingwebhookconfigurations
  - mutatingwebhookconfigurations
  verbs:
  - get
  - update
- apiGroups:
  - policy
  resources:
  - podsecuritypolicies
  verbs:
  - use
EOF

# clusterrolebinding:
kubectl create clusterrolebinding "${APP_INSTANCE_NAME}:kube-promethe-admissionServiceAccount" \
    --namespace="${NAMESPACE}" \
    --clusterrole="${NAMESPACE}:${APP_INSTANCE_NAME}:kube-promethe-admissionServiceAccount" \
    --serviceaccount="${NAMESPACE}:${APP_INSTANCE_NAME}-kube-promethe-admissionserviceaccount"
kubectl label clusterrolebindings "${APP_INSTANCE_NAME}:kube-promethe-admissionServiceAccount" app.kubernetes.io/name="${APP_INSTANCE_NAME}" \
    --namespace="${NAMESPACE}"
```

##### kube-promethe-operator

```bash
# service account:
kubectl create serviceaccount "${APP_INSTANCE_NAME}-kube-promethe-operatorserviceaccount" \
    --namespace="${NAMESPACE}"
kubectl label serviceaccount "${APP_INSTANCE_NAME}-kube-promethe-operatorserviceaccount" app.kubernetes.io/name="${APP_INSTANCE_NAME}" \
    --namespace="${NAMESPACE}"

# clusterrole:
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  labels:
    app.kubernetes.io/name: ${APP_INSTANCE_NAME}
    app.kubernetes.io/namespace: "${NAMESPACE}"
  name: ${NAMESPACE}:${APP_INSTANCE_NAME}:kube-promethe-operatorServiceAccount
rules:
- apiGroups:
  - monitoring.coreos.com
  resources:
  - alertmanagers
  - alertmanagers/finalizers
  - alertmanagerconfigs
  - prometheuses
  - prometheuses/finalizers
  - thanosrulers
  - thanosrulers/finalizers
  - servicemonitors
  - podmonitors
  - probes
  - prometheusrules
  verbs:
  - '*'
- apiGroups:
  - apps
  resources:
  - statefulsets
  verbs:
  - '*'
- apiGroups:
  - ""
  resources:
  - configmaps
  - secrets
  verbs:
  - '*'
- apiGroups:
  - ""
  resources:
  - pods
  verbs:
  - list
  - delete
- apiGroups:
  - ""
  resources:
  - services
  - services/finalizers
  - endpoints
  verbs:
  - get
  - create
  - update
  - delete
- apiGroups:
  - ""
  resources:
  - nodes
  verbs:
  - list
  - watch
- apiGroups:
  - ""
  resources:
  - namespaces
  verbs:
  - get
  - list
  - watch
- apiGroups:
  - networking.k8s.io
  resources:
  - ingress
  verbs:
  - get
  - list
  - watch
- apiGroups:
  - policy
  resources:
  - podsecuritypolicies
  verbs:
  - use
EOF

# clusterrolebinding:
kubectl create clusterrolebinding "${APP_INSTANCE_NAME}:kube-promethe-operatorServiceAccount" \
    --namespace="${NAMESPACE}" \
    --clusterrole="${NAMESPACE}:${APP_INSTANCE_NAME}:kube-promethe-operatorServiceAccount" \
    --serviceaccount="${NAMESPACE}:${APP_INSTANCE_NAME}-kube-promethe-operatorserviceaccount"
kubectl label clusterrolebindings "${APP_INSTANCE_NAME}:kube-promethe-operatorServiceAccount" app.kubernetes.io/name="${APP_INSTANCE_NAME}" \
    --namespace="${NAMESPACE}"
```

##### kube-promethe-prometheus

```bash
# service account:
kubectl create serviceaccount "${APP_INSTANCE_NAME}-kube-promethe-prometheusserviceaccount" \
    --namespace="${NAMESPACE}"
kubectl label serviceaccounts "${APP_INSTANCE_NAME}-kube-promethe-prometheusserviceaccount" app.kubernetes.io/name="${APP_INSTANCE_NAME}" \
    --namespace="${NAMESPACE}"

# clusterrole:
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  labels:
    app.kubernetes.io/name: "${APP_INSTANCE_NAME}"
    app.kubernetes.io/namespace: "${NAMESPACE}" 
  name: ${NAMESPACE}:${APP_INSTANCE_NAME}:kube-promethe-prometheusServiceAccount
rules:
- apiGroups:
  - ""
  resources:
  - nodes
  - nodes/metrics
  - services
  - endpoints
  - pods
  verbs:
  - get
  - list
  - watch
- apiGroups:
  - networking.k8s.io
  resources:
  - ingress
  verbs:
  - get
  - watch
  - list
- apiGroups:
  - policy
  resources:
  - podsecuritypolicies
  verbs:
  - use
EOF

# clusterrolebinding:
kubectl create clusterrolebinding "${APP_INSTANCE_NAME}:kube-promethe-prometheusServiceAccount" \
    --namespace="${NAMESPACE}" \
    --clusterrole="${NAMESPACE}:${APP_INSTANCE_NAME}:kube-promethe-prometheusServiceAccount" \
    --serviceaccount="${NAMESPACE}:${APP_INSTANCE_NAME}-kube-promethe-prometheusserviceaccount"
kubectl label clusterrolebindings "${APP_INSTANCE_NAME}:kube-promethe-prometheusServiceAccount" app.kubernetes.io/name="${APP_INSTANCE_NAME}" \
    --namespace="${NAMESPACE}"
```

#### Expand the manifest template

Use `helm template` to expand the template. We recommend that you save the expanded manifest file for future updates to the application.

```bash
helm template "${APP_INSTANCE_NAME}" chart/k8ssandra-mp \
    --namespace "${NAMESPACE}" \
    --include-crds \
    --set k8ssandra.cassandra.image.registry="${REGISTRY}" \
    --set k8ssandra.cassandra.image.repository="${REPOSITORY}/${IMAGE_CASSANDRA}" \
    --set k8ssandra.cassandra.image.tag="${TAG}" \
    --set k8ssandra.cassandra.configBuilder.image.registry="${REGISTRY}" \
    --set k8ssandra.cassandra.configBuilder.image.repository="${REPOSITORY}/${IMAGE_CASSANDRA_CONFIG_BUILDER}" \
    --set k8ssandra.cassandra.configBuilder.image.tag="${TAG}" \
    --set k8ssandra.cassandra.jmxCredentialsConfig.image.registry="${REGISTRY}" \
    --set k8ssandra.cassandra.jmxCredentialsConfig.image.repository="${REPOSITORY}/${IMAGE_JMX_CREDENTIALS_CONFIG}" \
    --set k8ssandra.cassandra.jmxCredentialsConfig.image.tag="${TAG}" \
    --set k8ssandra.cassandra.loggingSidecar.image.registry="${REGISTRY}" \
    --set k8ssandra.cassandra.loggingSidecar.image.repository="${REPOSITORY}/${IMAGE_LOGGING_SIDECAR}" \
    --set k8ssandra.cassandra.loggingSidecar.image.tag="${TAG}" \
    --set k8ssandra.stargate.image.registry="${REGISTRY}" \
    --set k8ssandra.stargate.image.repository="${REPOSITORY}/${IMAGE_STARGATE}" \
    --set k8ssandra.stargate.image.tag="${TAG}" \
    --set k8ssandra.stargate.waitForCassandra.image.registry="${REGISTRY}" \
    --set k8ssandra.stargate.waitForCassandra.image.repository="${REPOSITORY}/${IMAGE_WAIT_FOR_CASSANDRA}" \
    --set k8ssandra.stargate.waitForCassandra.image.tag="${TAG}" \
    --set k8ssandra.reaper.image.registry="${REGISTRY}" \
    --set k8ssandra.reaper.image.repository="${REPOSITORY}/${IMAGE_REAPER}" \
    --set k8ssandra.reaper.image.tag="${TAG}" \
    --set k8ssandra.medusa.image.registry="${REGISTRY}" \
    --set k8ssandra.medusa.image.repository="${REPOSITORY}/${IMAGE_MEDUSA}" \
    --set k8ssandra.medusa.image.tag="${TAG}" \
    --set k8ssandra.cleaner.image.registry="${REGISTRY}" \
    --set k8ssandra.cleaner.image.repository="${REPOSITORY}/${IMAGE_CLEANER}" \
    --set k8ssandra.cleaner.image.tag="${TAG}" \
    --set k8ssandra.client.image.registry="${REGISTRY}" \
    --set k8ssandra.client.image.repository="${REPOSITORY}/${IMAGE_CLIENT}" \
    --set k8ssandra.client.image.tag="${TAG}" \
    --set k8ssandra.cass-operator.image.registry="${REGISTRY}" \
    --set k8ssandra.cass-operator.image.repository="${REPOSITORY}/${IMAGE_CASS_OPERATOR}" \
    --set k8ssandra.cass-operator.image.tag="${TAG}" \
    --set k8ssandra.reaper-operator.image.registry="${REGISTRY}" \
    --set k8ssandra.reaper-operator.image.repository="${REPOSITORY}/${IMAGE_REAPER_OPERATOR}" \
    --set k8ssandra.reaper-operator.image.tag="${TAG}" \
    --set k8ssandra.medusa-operator.image.registry="${REGISTRY}" \
    --set k8ssandra.medusa-operator.image.repository="${REPOSITORY}/${IMAGE_MEDUSA_OPERATOR}" \
    --set k8ssandra.medusa-operator.image.tag="${TAG}" \
    --set k8ssandra.kube-prometheus-stack.prometheus-operator.image.registry="${REGISTRY}" \
    --set k8ssandra.kube-prometheus-stack.prometheus-operator.image.repository="${REPOSITORY}/${IMAGE_PROMETHEUS_OPERATOR}" \
    --set k8ssandra.kube-prometheus-stack.prometheus-operator.image.tag="${TAG}" \
    --set k8ssandra.kube-prometheus-stack.prometheus-operator.prometheusSpec.image.registry="${REGISTRY}" \
    --set k8ssandra.kube-prometheus-stack.prometheus-operator.prometheusSpec.image.repository="${REPOSITORY}/${IMAGE_PROMETHEUS_SPEC}" \
    --set k8ssandra.kube-prometheus-stack.prometheus-operator.prometheusSpec.image.tag="${TAG}" \
    --set k8ssandra.grafana.image.registry="${REGISTRY}" \
    --set k8ssandra.grafana.image.repository="${REPOSITORY}/${IMAGE_GRAFANA}" \
    --set k8ssandra.grafana.image.tag="${TAG}" \
    --set k8ssandra.kube-prometheus-stack.grafana.initChownData.image.registry="${REGISTRY}" \
    --set k8ssandra.kube-prometheus-stack.grafana.initChownData.image.repository="${REPOSITORY}/${IMAGE_INIT_CHOWN_DATA}" \
    --set k8ssandra.kube-prometheus-stack.grafana.initChownData.image.tag="${TAG}" \
    --set k8ssandra.kube-prometheus-stack.grafana.sidecar.image.repository="${REGISTRY}/${REPOSITORY}/${IMAGE_GRAFANA_SIDECAR}" \
    --set k8ssandra.kube-prometheus-stack.grafana.sidecar.image.tag="${TAG}" \
    --set k8ssandra.kube-prometheus-stack.grafana.imageRenderer.image.repository="${REGISTRY}/${REPOSITORY}" \
    --set k8ssandra.kube-prometheus-stack.grafana.imageRenderer.image.tag="${TAG}" \
    --set k8ssandra.cassandra.cassandraLibDirVolume.storageClass="${DEFAULT_STORAGE_CLASS}" \
    --set k8ssandra.cassandra.cassandraLibDirVolume.size="1Gi" \
    --set k8ssandra.cassandra.allowMultipleNodesPerWorker="true" \
    --set k8ssandra.cassandra.heap.size="1G" \
    --set k8ssandra.cassandra.heap.newGenSize="1G" \
    --set k8ssandra.cassandra.resources.requests.cpu="1000m" \
    --set k8ssandra.cassandra.resources.requests.memory="2Gi" \
    --set k8ssandra.cassandra.resources.limits.cpu="1000m" \
    --set k8ssandra.cassandra.resources.limits.memory="2Gi" \
    --set k8ssandra.reaper.enabled="true" \
    --set k8ssandra.reaper-operator.enabled="true" \
    --set k8ssandra.stargate.enabled="true" \
    --set k8ssandra.kube-prometheus-stack.enabled="true" \
    > "${APP_INSTANCE_NAME}_manifest.yaml"
```

#### Patch the manifest

We explicitly created the service accounts and RBAC resources above, so we need to modify the manifest to account for this.

```bash
./scripts/patch-manifest.sh "${APP_INSTANCE_NAME}"
```

This will replace default service account names and include common labels needed for the proper execution in the Google Cloud Marketplace environment.

#### Apply the manifest to your Kubernetes cluster

First use `kubectl` to apply the CustomResourceDefinitions to your Kubernetes cluster:

```bash
kubectl apply -f "${APP_INSTANCE_NAME}_manifest.yaml" \
    --namespace="${NAMESPACE}" \
    --selector is-crd=yes || true

sleep 5

# We need to apply a second time here to work-around resource order of creation issues.

kubectl apply -f "${APP_INSTANCE_NAME}_manifest.yaml" \
    --namespace="${NAMESPACE}" \
    --selector is-crd=yes

# Give enough time for CRDs to be available in the Kubernets cluster.
sleep 60
```

Next, use `kubectl` to apply all the other resources to your Kubernetes cluster:

```bash
kubectl apply -f "${APP_INSTANCE_NAME}_manifest.yaml" \
    --namespace "${NAMESPACE}" \
    --selector excluded-resource=no,is-crd=no
```

# Uninstall the Application

## Using the Google Cloud Platform Console

1. In the GCP Console, open [Kubernetes Applications].
2. From the list of applications, click **k8ssandra-mp**.
3. On the Application Details page, click **Delete**.

## Using the command line

### Prepare the environment

Set your installation name and Kubernetes namespace:

```bash
export APP_INSTANCE_NAME=k8ssandra-mp
export NAMESPACE=default
```

### Delete the resources

First delete the cassandradatacenter resources:

```bash
kubectl delete cassandradatacenter \
    --namespace "${NAMESPACE}" \
    --selector app.kubernetes.io/name="${APP_INSTANCE_NAME}"
```

Resources of this type need to be deleted prior to the cass-operator deployment. The cass-operator deployment will be deleted during the next step, so it's important that this gets run first.

Delete all other Application resources:

```bash
for resource_type in \
    application \
    clusterrole \
    clusterrolebinding \
    configmap \
    deployment \
    job \
    mutatingwebhookconfiguration \
    persistentvolume \
    persistentvolumeclaim \
    pod \
    podsecuritypolicy \
    prometheus \
    prometheusrule \
    reaper \
    replicaset \
    role \
    rolebinding \
    secret \
    service \
    serviceaccount \
    servicemonitor \
    statefulset \
    validatingwebhookconfiguration; do

    kubectl delete "${resource_type}" \
        --selector app.kubernetes.io/name="${APP_INSTANCE_NAME}" \
        --namespace "${NAMESPACE}"
done
```
