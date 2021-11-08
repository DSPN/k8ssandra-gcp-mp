# Overview
Built on the rock-solid Apache Cassandra® NoSQL database, K8ssandra brings together a complete operational data platform for Kubernetes including APIs, monitoring, and backups.

# Installation

## Quick install with Google Cloud Marketplace
Get up and running with a few clicks! Install the k8ssandra marketplace app to a Google Kubernetes Engine cluster by using Google Cloud Marketplace. Follow the [[on-screen-instructions]](https://google.com)

## Command-line instructions
You can use [Google Cloud Shell] or a local workstation to follow the steps below.

### Prerequisites

#### Set up command-line tools

You'll need the following tools in your development environment. If you are using Cloud Shell, gcloud, kubectl, Docker, git, helm, and kustomize are installed in your environment by default.

* [gcloud](https://cloud.google.com/sdk/gcloud/)
* [kubectl](https://kubernetes.io/docs/reference/kubectl/overview/)
* [docker](https://docs.docker.com/install/)
* [git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
* [helm](https://helm.sh/)
* [kustomize](https://kustomize.io/)

Configure gcloud as a docker credential helper:

```
gcloud auth configure-docker
```

#### Create a Google Kubernetes Engine cluster

Create a new cluster from the command line:

```
export CLUSTER=k8ssandra-mp-cluster
export ZONE=us-central1-a
gcloud container clusters create "${CLUSTER}" --zone "$ZONE"
```

Configure kubectl to connect to the cluster:

```
gcloud container clusters get-credentials "${CLUSTER}" --zone "${ZONE}"
```

#### Clone this repo

```
git clone https://github.com/DSPN/k8ssandra-gcp-mp.git
```

#### Install the Application resource definition

An Application resource is a collection of individual Kubernetes components, such as Services, Deployments, and so on, that you can manage as a group.

To set up your cluster to understand Application resources, run the following command:

```
kubectl apply -f "https://raw.githubusercontent.com/GoogleCloudPlatform/marketplace-k8s-app-tools/master/crd/app-crd.yaml"
```

You need to run this command once.

The Application resource is defined by the [Kubernetes SIG-apps](https://github.com/kubernetes/community/tree/master/sig-apps) community. The source code can be found on [github.com/kubernetes-sigs/application](https://github.com/kubernetes-sigs/application).

#### Download the k8ssandra charts

```
helm repo add k8ssandra https://helm.k8ssandra.io/stable
helm dependency build chart/k8ssandra-mp
```

### Install the Application

#### Configure the app with environment variables

Choose an instance name and namespace for the app. In most cases you can use the `default` namespace.

```
export APP_INSTANCE_NAME=k8ssandra-mp
export NAMESPACE=default
export DEFAULT_STORAGE_CLASS=k8ssandra-storage
```

#### Create a suitable storage class

Create a storage class that will be used by the Cassandra persistent storage volume claims:

```
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

```
kubectl create namespace "${NAMESPACE}"
```

#### Create service accounts and RBAC resources

##### grafana

```
kubectl create serviceaccount "${APP_INSTANCE_NAME}-grafanaserviceaccount" \
    --namespace="${NAMESPACE}"
```

```
kubectl create role "${APP_INSTANCE_NAME}:grafanaServiceAccount" \
    --namespace="${NAMESPACE}" \
    --verb=use,get,list,watch \
    --resource=extensions,"",podsecuritypolicies,secrets,configmaps
```

```
kubectl create rolebinding "${APP_INSTANCE_NAME}:grafanaServiceAccount \
    --namespace="${NAMESPACE}" \
    --role="${APP_INSTANCE_NAME}:grafanaServiceAccount" \
    --serviceaccount="${NAMESPACE}:${APP_INSTANCE_NAME}-grafanaserviceaccount
```

##### cass-operator

```
kubectl create serviceaccount "${APP_INSTANCE_NAME}-cass-operatorserviceaccount" \
    --namespace="${NAMESPACE}"
```

```
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
```

```
kubectl create rolebinding "${APP_INSTANCE_NAME}:cass-operatorServiceAccount \
    --namespace="${NAMESPACE}" \
    --role="${APP_INSTANCE_NAME}:cass-operatorServiceAccount" \
    --serviceaccount="${NAMESPACE}:${APP_INSTANCE_NAME}-cass-operatorserviceaccount
```

```
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
```

```
kubectl create clusterrolebinding "${APP_INSTANCE_NAME}:cass-operatorServiceAccount \
    --namespace="${NAMESPACE}" \
    --clusterrole="${APP_INSTANCE_NAME}:cass-operatorServiceAccount" \
    --serviceaccount="${NAMESPACE}:${APP_INSTANCE_NAME}-cass-operatorserviceaccount
```

##### kube-promethe-admission

```
kubectl create serviceaccount "${APP_INSTANCE_NAME}-kube-promethe-admissionserviceaccount" \
    --namespace="${NAMESPACE}"
```

```
kubectl create role "${APP_INSTANCE_NAME}:kube-promethe-admissionServiceAccount" \
    --namespace="${NAMESPACE}" \
    --verb=get,create \
    --resource="",secrets,configmaps
```

```
kubectl create rolebinding "${APP_INSTANCE_NAME}:kube-promethe-admissionServiceAccount \
    --namespace="${NAMESPACE}" \
    --role="${APP_INSTANCE_NAME}:kube-promethe-admissionServiceAccount" \
    --serviceaccount="${NAMESPACE}:${APP_INSTANCE_NAME}-kube-promethe-admissionserviceaccount
```

```
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
```

```
kubectl create clusterrolebinding "${APP_INSTANCE_NAME}:kube-promethe-admissionServiceAccount \
    --namespace="${NAMESPACE}" \
    --clusterrole="${NAMESPACE}:${APP_INSTANCE_NAME}:kube-promethe-admissionServiceAccount" \
    --serviceaccount="${NAMESPACE}:${APP_INSTANCE_NAME}-kube-promethe-admissionserviceaccount
```

##### kube-promethe-operator

```
kubectl create serviceaccount "${APP_INSTANCE_NAME}-kube-promethe-operatorserviceaccount" \
    --namespace="${NAMESPACE}"
```

```
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
```

```
kubectl create clusterrolebinding "${APP_INSTANCE_NAME}:kube-promethe-operatorServiceAccount \
    --namespace="${NAMESPACE}" \
    --clusterrole="${NAMESPACE}:${APP_INSTANCE_NAME}:kube-promethe-operatorServiceAccount" \
    --serviceaccount="${NAMESPACE}:${APP_INSTANCE_NAME}-kube-promethe-operatorserviceaccount
```

##### kube-promethe-prometheus

```
kubectl create serviceaccount "${APP_INSTANCE_NAME}-kube-promethe-prometheusserviceaccount" \
    --namespace="${NAMESPACE}"
```

```
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
```

#### Expand the manifest template

Use `helm template` to expand the template. We recommend that you save the expanded manifest file for future updates to the application.

```
helm template "${APP_INSTANCE_NAME}" chart/k8ssandra-mp \
    --namespace "${NAMESPACE}" \
    --include-crds \
    > "${APP_INSTANCE_NAME}_manifest.yaml"
```

#### Patch the manifest

We explicitly created the service accounts and RBAC resources above, so we need to modify the manifest to account for this.

```
./scripts/patch-manifest.sh "${APP_INSTANCE_NAME}"
```

This will replace default service account names and include common labels needed for the proper execution in the Google Cloud Marketplace environment.

#### Apply the manifest to your Kubernetes cluster

Use `kubectl` to apply the manifest to your Kubernetes cluster:

```
kubectl apply -f "${APP_INSTANCE_NAME}_manifest.yaml" --namespace "${NAMESPACE}"
```

# Basic usage

# Back up and restore

# Image updates

# Scaling

# Deletion

