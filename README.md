# Overview
Built on the rock-solid Apache Cassandra® NoSQL database, K8ssandra brings together a complete operational data platform for Kubernetes including APIs, monitoring, and backups.

# Installation

## Quick install with Google Cloud Marketplace
Get up and running with a few clicks! Install the k8ssandra marketplace app to a Google Kubernetes Engine cluster by using Google Cloud Marketplace. Follow the [on-screen-instructions](https://console.cloud.google.com/marketplace/details/datastax-public/k8ssandra-marketplace)

## Command-line instructions
You can use [Google Cloud Shell](https://console.cloud.google.com/home/dashboard?cloudshell=true&_ga=2.56087010.819465746.1651092702-2069899356.1630444315) or a local workstation to follow the steps below.

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
export CLUSTER_SIZE=3
export ZONE=us-west1-a
export RELEASE_CHANNEL=regular
gcloud container clusters create "${CLUSTER}" \
    --zone "$ZONE" \
    --release-channel "$RELEASE_CHANNEL" \
    --machine-type n2-standard-2 \
    --num-nodes "$CLUSTER_SIZE"
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

### Download and apply the license key

As described in the "DEPLOY VIA COMMAND LINE" section of the Marketplace listing, you need to download the license key for k8ssandra-marketplace. You may have already done this, and if so, you can skip this section. Other wise, visit the [k8ssandra-marketplace configuration UI](https://console.cloud.google.com/marketplace/kubernetes/config/datastax-public/k8ssandra-marketplace?version=1.3) and click on "DEPLOY VIA COMMAND LINE". Then follow the instructions on the screen for step 1 and 2.

### Install the Application

#### Navigate to the k8ssandra-gcp-mp directory

```bash
cd k8ssandra-gcp-mp
```

#### Download the k8ssandra charts

```bash
helm repo add k8ssandra https://helm.k8ssandra.io/stable
helm dependency build chart/k8ssandra-marketplace
```

#### Configure the app with environment variables

Choose an instance name, namespace, and default storage class for the app. In most cases you can use the `default` namespace.

```bash
export APP_INSTANCE_NAME=k8ssandra-marketplace
export NAMESPACE=default
export DEFAULT_STORAGE_CLASS=k8ssandra-storage
export DC_SIZE=3
```

Set up the image registry, repository, and tag:

```bash
export REGISTRY="gcr.io"
export REPOSITORY="datastax-public/k8ssandra-mp"
export TAG="1.3"
```

Configure the container images:

```bash
export IMAGE_CASS_OPERATOR="cass-operator"
export IMAGE_CASSANDRA_CONFIG_BUILDER="cassandra-config-builder"
export IMAGE_CASSANDRA_JMX_CREDENTIALS="cassandra-jmx-credentials"
export IMAGE_CASSANDRA_SYSTEM_LOGGER="cassandra-system-logger"
export IMAGE_CLEANER="cleaner"
export IMAGE_CLIENT="client"
export IMAGE_GRAFANA="grafana"
export IMAGE_GRAFANA_SIDECAR="grafana-sidecar"
export IMAGE_KUBE_PROMETHEUS_STACK_ADMISSION_PATCH="kube-prometheus-stack-admission-patch"
export IMAGE_MEDUSA="medusa"
export IMAGE_MEDUSA_OPERATOR="medusa-operator"
export IMAGE_PROMETHEUS="prometheus"
export IMAGE_PROMETHEUS_CONFIG_RELOADER="prometheus-config-reloader"
export IMAGE_PROMETHEUS_OPERATOR="prometheus-operator"
export IMAGE_REAPER="reaper"
export IMAGE_REAPER_OPERATOR="reaper-operator"
export IMAGE_STARGATE="stargate"
export IMAGE_STARGATE_WAIT_FOR_CASSANDRA="stargate-wait-for-cassandra"
export IMAGE_ADMISSION_CONTROLLER="admission-controller"
export IMAGE_UBBAGENT="ubbagent"
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

#### Extract and export the reporting secret name

In a previous step, you downloaded and applied the license key to your cluster. In this step, you'll extract the name of the kubernetes secret that contains that key and make it available for use in the helm chart templates.

```bash
REPORTING_SECRET="$(kubectl --namespace="${NAMESPACE}" get secret | grep "^${APP_INSTANCE_NAME}-license" | awk -F' ' '{print $1}')"
export REPORTING_SECRET
```

#### Create service accounts and RBAC resources for each of the k8ssandra components

##### grafana

```bash
#service account:
kubectl create serviceaccount "${APP_INSTANCE_NAME}-grafana-sa" \
    --namespace="${NAMESPACE}"
kubectl label serviceaccounts "${APP_INSTANCE_NAME}-grafana-sa" app.kubernetes.io/name="${APP_INSTANCE_NAME}" \
    --namespace="${NAMESPACE}"

#role:
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  labels:
    app.kubernetes.io/name: ${NAMESPACE}
  name: ${APP_INSTANCE_NAME}:grafana-sa
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
kubectl create rolebinding "${APP_INSTANCE_NAME}:grafana-sa" \
    --namespace="${NAMESPACE}" \
    --role="${APP_INSTANCE_NAME}:grafana-sa" \
    --serviceaccount="${NAMESPACE}:${APP_INSTANCE_NAME}-grafana-sa"
kubectl label rolebindings "${APP_INSTANCE_NAME}:grafana-sa" app.kubernetes.io/name="${APP_INSTANCE_NAME}" \
    --namespace="${NAMESPACE}"
```

##### cass-operator

```bash
#service account:
kubectl create serviceaccount "${APP_INSTANCE_NAME}-cass-operator-sa" \
    --namespace="${NAMESPACE}"
kubectl label serviceaccounts "${APP_INSTANCE_NAME}-cass-operator-sa" app.kubernetes.io/name="${APP_INSTANCE_NAME}" \
    --namespace="${NAMESPACE}"

#role:
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  labels:
    app.kubernetes.io/name: ${APP_INSTANCE_NAME}
  name: "${APP_INSTANCE_NAME}:cass-operator-sa"
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
kubectl create rolebinding "${APP_INSTANCE_NAME}:cass-operator-sa" \
    --namespace="${NAMESPACE}" \
    --role="${APP_INSTANCE_NAME}:cass-operator-sa" \
    --serviceaccount="${NAMESPACE}:${APP_INSTANCE_NAME}-cass-operator-sa"
kubectl label rolebindings "${APP_INSTANCE_NAME}:cass-operator-sa" app.kubernetes.io/name="${APP_INSTANCE_NAME}" \
    --namespace="${NAMESPACE}"

# clusterrole:
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  labels:
    app.kubernetes.io/name: ${APP_INSTANCE_NAME}
  name: "${APP_INSTANCE_NAME}:cass-operator-sa"
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
kubectl create clusterrolebinding "${APP_INSTANCE_NAME}:cass-operator-sa" \
    --namespace="${NAMESPACE}" \
    --clusterrole="${APP_INSTANCE_NAME}:cass-operator-sa" \
    --serviceaccount="${NAMESPACE}:${APP_INSTANCE_NAME}-cass-operator-sa"
kubectl label clusterrolebindings "${APP_INSTANCE_NAME}:cass-operator-sa" app.kubernetes.io/name="${APP_INSTANCE_NAME}" \
    --namespace="${NAMESPACE}"
```

##### kube-promethe-admission

```bash
# service account:
kubectl create serviceaccount "${APP_INSTANCE_NAME}-webhook-admiss-sa" \
    --namespace="${NAMESPACE}"
kubectl label serviceaccounts "${APP_INSTANCE_NAME}-webhook-admiss-sa" app.kubernetes.io/name="${APP_INSTANCE_NAME}" \
    --namespace="${NAMESPACE}"

# role:
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  labels:
    app.kubernetes.io/name: ${APP_INSTANCE_NAME}
  name: ${APP_INSTANCE_NAME}:webhook-admiss-sa
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
kubectl create rolebinding "${APP_INSTANCE_NAME}:webhook-admiss-sa" \
    --namespace="${NAMESPACE}" \
    --role="${APP_INSTANCE_NAME}:webhook-admiss-sa" \
    --serviceaccount="${NAMESPACE}:${APP_INSTANCE_NAME}-webhook-admiss-sa"
kubectl label rolebindings "${APP_INSTANCE_NAME}:webhook-admiss-sa" app.kubernetes.io/name="${APP_INSTANCE_NAME}" \
    --namespace="${NAMESPACE}"

# clusterrole:
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  labels:
    app.kubernetes.io/name: ${APP_INSTANCE_NAME}
    app.kubernetes.io/namespace: "${NAMESPACE}"
  name: ${NAMESPACE}:${APP_INSTANCE_NAME}:webhook-admiss-sa
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
kubectl create clusterrolebinding "${APP_INSTANCE_NAME}:webhook-admiss-sa" \
    --namespace="${NAMESPACE}" \
    --clusterrole="${NAMESPACE}:${APP_INSTANCE_NAME}:webhook-admiss-sa" \
    --serviceaccount="${NAMESPACE}:${APP_INSTANCE_NAME}-webhook-admiss-sa"
kubectl label clusterrolebindings "${APP_INSTANCE_NAME}:webhook-admiss-sa" app.kubernetes.io/name="${APP_INSTANCE_NAME}" \
    --namespace="${NAMESPACE}"
```

##### kube-promethe-operator

```bash
# service account:
kubectl create serviceaccount "${APP_INSTANCE_NAME}-prom-operator-sa" \
    --namespace="${NAMESPACE}"
kubectl label serviceaccount "${APP_INSTANCE_NAME}-prom-operator-sa" app.kubernetes.io/name="${APP_INSTANCE_NAME}" \
    --namespace="${NAMESPACE}"

# clusterrole:
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  labels:
    app.kubernetes.io/name: ${APP_INSTANCE_NAME}
    app.kubernetes.io/namespace: "${NAMESPACE}"
  name: ${NAMESPACE}:${APP_INSTANCE_NAME}:prom-operator-sa
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
kubectl create clusterrolebinding "${APP_INSTANCE_NAME}:prom-operator-sa" \
    --namespace="${NAMESPACE}" \
    --clusterrole="${NAMESPACE}:${APP_INSTANCE_NAME}:prom-operator-sa" \
    --serviceaccount="${NAMESPACE}:${APP_INSTANCE_NAME}-prom-operator-sa"
kubectl label clusterrolebindings "${APP_INSTANCE_NAME}:prom-operator-sa" app.kubernetes.io/name="${APP_INSTANCE_NAME}" \
    --namespace="${NAMESPACE}"
```

##### kube-promethe-prometheus

```bash
# service account:
kubectl create serviceaccount "${APP_INSTANCE_NAME}-prometheus-sa" \
    --namespace="${NAMESPACE}"
kubectl label serviceaccounts "${APP_INSTANCE_NAME}-prometheus-sa" app.kubernetes.io/name="${APP_INSTANCE_NAME}" \
    --namespace="${NAMESPACE}"

# clusterrole:
cat <<EOF | kubectl apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  labels:
    app.kubernetes.io/name: "${APP_INSTANCE_NAME}"
    app.kubernetes.io/namespace: "${NAMESPACE}" 
  name: ${NAMESPACE}:${APP_INSTANCE_NAME}:prometheus-sa
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
kubectl create clusterrolebinding "${APP_INSTANCE_NAME}:prometheus-sa" \
    --namespace="${NAMESPACE}" \
    --clusterrole="${NAMESPACE}:${APP_INSTANCE_NAME}:prometheus-sa" \
    --serviceaccount="${NAMESPACE}:${APP_INSTANCE_NAME}-prometheus-sa"
kubectl label clusterrolebindings "${APP_INSTANCE_NAME}:prometheus-sa" app.kubernetes.io/name="${APP_INSTANCE_NAME}" \
    --namespace="${NAMESPACE}"
```

#### Expand the manifest template

Use `helm template` to expand the template. We recommend that you save the expanded manifest file for future updates to the application.

```bash
helm template "${APP_INSTANCE_NAME}" chart/k8ssandra-marketplace \
    --namespace "${NAMESPACE}" \
    --include-crds \
    --set k8ssandra.cassandra.image.registry="${REGISTRY}" \
    --set k8ssandra.cassandra.image.repository="${REPOSITORY}" \
    --set k8ssandra.cassandra.image.tag="${TAG}" \
    --set k8ssandra.cassandra.configBuilder.image.registry="${REGISTRY}" \
    --set k8ssandra.cassandra.configBuilder.image.repository="${REPOSITORY}/${IMAGE_CASSANDRA_CONFIG_BUILDER}" \
    --set k8ssandra.cassandra.configBuilder.image.tag="${TAG}" \
    --set k8ssandra.cassandra.jmxCredentialsConfig.image.registry="${REGISTRY}" \
    --set k8ssandra.cassandra.jmxCredentialsConfig.image.repository="${REPOSITORY}/${IMAGE_CASSANDRA_JMX_CREDENTIALS}" \
    --set k8ssandra.cassandra.jmxCredentialsConfig.image.tag="${TAG}" \
    --set k8ssandra.cassandra.loggingSidecar.image.registry="${REGISTRY}" \
    --set k8ssandra.cassandra.loggingSidecar.image.repository="${REPOSITORY}/${IMAGE_CASSANDRA_SYSTEM_LOGGER}" \
    --set k8ssandra.cassandra.loggingSidecar.image.tag="${TAG}" \
    --set k8ssandra.stargate.image.registry="${REGISTRY}" \
    --set k8ssandra.stargate.image.repository="${REPOSITORY}/${IMAGE_STARGATE}" \
    --set k8ssandra.stargate.image.tag="${TAG}" \
    --set k8ssandra.stargate.waitForCassandra.image.registry="${REGISTRY}" \
    --set k8ssandra.stargate.waitForCassandra.image.repository="${REPOSITORY}/${IMAGE_STARGATE_WAIT_FOR_CASSANDRA}" \
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
    --set k8ssandra.kube-prometheus-stack.prometheus.prometheusSpec.image.repository="${REGISTRY}/${REPOSITORY}/${IMAGE_PROMETHEUS}" \
    --set k8ssandra.kube-prometheus-stack.prometheus.prometheusSpec.image.tag="${TAG}" \
    --set k8ssandra.kube-prometheus-stack.prometheusOperator.image.repository="${REGISTRY}/${REPOSITORY}/${IMAGE_PROMETHEUS_OPERATOR}" \
    --set k8ssandra.kube-prometheus-stack.prometheusOperator.image.tag="${TAG}" \
    --set k8ssandra.kube-prometheus-stack.prometheusOperator.prometheusConfigReloaderImage.repository="${REGISTRY}/${REPOSITORY}/${IMAGE_PROMETHEUS_CONFIG_RELOADER}" \
    --set k8ssandra.kube-prometheus-stack.prometheusOperator.prometheusConfigReloaderImage.tag="${TAG}" \
    --set k8ssandra.kube-prometheus-stack.prometheusOperator.admissionWebhooks.patch.image.repository="${REGISTRY}/${REPOSITORY}/${IMAGE_KUBE_PROMETHEUS_STACK_ADMISSION_PATCH}" \
    --set k8ssandra.kube-prometheus-stack.prometheusOperator.admissionWebhooks.patch.image.tag="${TAG}" \
    --set k8ssandra.kube-prometheus-stack.grafana.image.repository="${REGISTRY}/${REPOSITORY}/${IMAGE_GRAFANA}" \
    --set k8ssandra.kube-prometheus-stack.grafana.image.tag="${TAG}" \
    --set k8ssandra.kube-prometheus-stack.grafana.sidecar.image.repository="${REGISTRY}/${REPOSITORY}/${IMAGE_GRAFANA_SIDECAR}" \
    --set k8ssandra.kube-prometheus-stack.grafana.sidecar.image.tag="${TAG}" \
    --set admiss-ctrl-image-repository="${REGISTRY}/${IMAGE_ADMISSION_CONTROLLER}:${TAG}" \
    --set ubbagent-image-repository="${REGISTRY}/${IMAGE_UBBAGENT}:${TAG}" \
    --set k8ssandra.cassandra.cassandraLibDirVolume.storageClass="${DEFAULT_STORAGE_CLASS}" \
    --set k8ssandra.cassandra.cassandraLibDirVolume.size="1Gi" \
    --set k8ssandra.cassandra.allowMultipleNodesPerWorker="true" \
    --set k8ssandra.cassandra.heap.size="1G" \
    --set k8ssandra.cassandra.heap.newGenSize="1G" \
    --set k8ssandra.cassandra.resources.requests.cpu="1000m" \
    --set k8ssandra.cassandra.resources.requests.memory="2Gi" \
    --set k8ssandra.cassandra.resources.limits.cpu="1000m" \
    --set k8ssandra.cassandra.resources.limits.memory="2Gi" \
    --set k8ssandra.cassandra.datacenters\[0].name=dc1 \
    --set k8ssandra.cassandra.datacenters\[0].size="$DC_SIZE" \
    --set k8ssandra.reaper.enabled="true" \
    --set k8ssandra.reaper-operator.enabled="true" \
    --set k8ssandra.stargate.enabled="true" \
    --set k8ssandra.kube-prometheus-stack.enabled="true" \
    --set k8ssandra.stargate.livenessInitialDelaySeconds="240" \
    --set k8ssandra.stargate.readinessInitialDelaySeconds="240" \
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

#### Wait for the Application components to become available

It will take about 10 or 15 minutes for all the components of k8ssandra to become fully available and ready to use. You can follow the status of the install process with the following command:

```bash
watch kubectl get pods --namespace "$NAMESPACE"
```

OUTPUT:

```
NAME                                                   READY   STATUS      RESTARTS   AGE
k8ssandra-mp-cass-operator-db4b9b67f-pfkd2             1/1     Running     0          27m
k8ssandra-mp-dc1-default-sts-0                         2/2     Running     0          26m
k8ssandra-mp-dc1-default-sts-1                         2/2     Running     0          26m
k8ssandra-mp-dc1-default-sts-2                         2/2     Running     0          26m
k8ssandra-mp-dc1-default-sts-3                         2/2     Running     0          26m
k8ssandra-mp-dc1-stargate-5d758d7499-4n8fz             1/1     Running     0          27m
k8ssandra-mp-grafana-6c9f769d6-t7khk                   2/2     Running     0          27m
k8ssandra-mp-kube-promethe-admission-create-xpg5b      0/1     Completed   0          27m
k8ssandra-mp-kube-promethe-admission-patch-brc7d       0/1     Completed   2          27m
k8ssandra-mp-kube-promethe-operator-7b4b746869-fhtwk   1/1     Running     0          27m
k8ssandra-mp-reaper-7d8c47fcd4-l4rbr                   1/1     Running     0          20m
k8ssandra-mp-reaper-operator-5c6589c7c9-np2c6          1/1     Running     0          27m
prometheus-k8ssandra-mp-kube-promethe-prometheus-0     2/2     Running     1          26m
```

When you see the stargate pod show 1/1 READY the application has been fully provisioned and is ready for use.

#### View the app in the Google Cloud Console

To get the GCP Console URL for your app, run the following command:

```bash
echo "https://console.cloud.google.com/kubernetes/application/${ZONE}/${CLUSTER}/${NAMESPACE}/${APP_INSTANCE_NAME}"
```

To view the app, open the URL in your browser.

#### Check the status of Cassandra

To be able to use Cassandra utilities you first need to retrieve the credentials for the Cassandra superuser. You can do that as follows:

username:
```bash
export CASS_USER=$(kubectl get secret ${APP_INSTANCE_NAME}-superuser -o jsonpath="{.data.username}" --namespace "$NAMESPACE" | base64 --decode ; echo)
echo $CASS_USER
```

password:
```bash
export CASS_PASS=$(kubectl get secret ${APP_INSTANCE_NAME}-superuser -o jsonpath="{.data.password}" --namespace "$NAMESPACE" | base64 --decode ; echo)
echo $CASS_PASS
```

Save both the username and password for future operations on the Cassandra cluster.

Now you can use `nodetool status` to check the status of Cassandra:

* Get a list of the pods with `kubectl get pods --namespace "$NAMESPACE"`
* Note: the k8ssandra pod running Cassandra takes the form `<k8ssandra-cluster-name>-<datacenter-name>-default-sts-<n>`
* run :

```bash
kubectl exec -it ${APP_INSTANCE_NAME}-dc1-default-sts-0 -c cassandra --namespace "$NAMESPACE" -- nodetool -u $CASS_USER -pw $CASS_PASS status
```

example output:

```
Datacenter: dc1
===============
Status=Up/Down
|/ State=Normal/Leaving/Joining/Moving
--  Address     Load       Tokens       Owns    Host ID                               Rack
UN  10.36.3.6   259.63 KiB  256          ?       d61b86a4-4484-44cb-958f-cb343a4c61a4  default
UN  10.36.2.6   251.37 KiB  256          ?       b772b997-7e28-479e-822f-78020cc9821b  default
UN  10.36.0.6   314.41 KiB  256          ?       d0473406-2872-461f-ab56-aeeebde2551a  default
UN  10.36.1.11  239.61 KiB  256          ?       b4396a21-bd14-49e7-b629-a50fe96929bc  default
```

For more operations please see the official k8ssandra getting started docs:

[Site Reliability Engineers](https://docs.k8ssandra.io/quickstarts/site-reliability-engineer/)

[Developers](https://docs.k8ssandra.io/quickstarts/developer/)

# Uninstall the Application

## Using the Google Cloud Platform Console

1. In the GCP Console, open [Kubernetes Applications].
2. From the list of applications, click **k8ssandra-mp**.
3. On the Application Details page, click **Delete**.

## Using the command line

### Prepare the environment

Set your installation name and Kubernetes namespace:

```bash
export APP_INSTANCE_NAME=k8ssandra-marketplace
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
