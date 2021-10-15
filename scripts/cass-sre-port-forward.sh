kubectl -n mallen port-forward svc/k8ssandra-mp-grafana 9191:80 &
kubectl -n mallen port-forward svc/prometheus-operated 9292:9090 &
kubectl -n mallen port-forward svc/k8ssandra-mp-reaper-reaper-service 9393:8080 &

