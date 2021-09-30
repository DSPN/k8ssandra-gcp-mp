kubectl -n mallen get secret k8ssandra-mp-superuser -o jsonpath="{.data.username}" | base64 --decode ; echo
kubectl -n mallen get secret k8ssandra-mp-superuser -o jsonpath="{.data.password}" | base64 --decode ; echo
