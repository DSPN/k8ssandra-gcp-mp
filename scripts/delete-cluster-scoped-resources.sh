#!/bin/bash

for r in psp \
         clusterrole \
         clusterrolebinding \
         validatingwebhookconfiguration \
         mutatingwebhookconfiguration; do
    kubectl delete "$r" -l app.kubernetes.io/name=k8ssandra-mp
done

