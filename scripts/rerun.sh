kubectl delete ns mallen
kubectl create ns mallen
sleep 2
docker build --tag $REGISTRY/$APP_NAME/deployer .
sleep 2
docker push $REGISTRY/$APP_NAME/deployer
sleep 4
mpdev install --deployer=$REGISTRY/$APP_NAME/deployer --parameters='{"name": "k8ssandra-mp", "namespace": "mallen"}'

