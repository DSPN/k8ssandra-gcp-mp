#!/bin/bash

cass_pass=$(kubectl -n mallen get secret k8ssandra-mp-superuser -o jsonpath="{.data.password}" | base64 --decode)

echo $cass_pass
curl -L -X POST 'http://localhost:8081/v1/auth' -H 'Content-Type: application/json' --data-raw "{\"username\": \"k8ssandra-mp-superuser\", \"password\": \"$cass_pass\"}"

