#!/bin/bash

namespace="ricxapp"
xapp_name="xapp4rmrsubreact"

echo "namespace=$namespace"
echo "xapp_name=$xapp_name"
curl http://$(kubectl get svc -n $namespace | grep $namespace-$xapp_name-http | awk '{print $3}'):8080/ric/v1/resubscribe
