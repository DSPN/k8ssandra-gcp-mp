#!/bin/bash

kubectl api-resources --verbs=list -o name \
  | xargs -n 1 kubectl get --show-kind --ignore-not-found -l app.kubernetes.io/name=k8ssandra-mp

