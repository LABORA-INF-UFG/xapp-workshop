#!/bin/bash
echo "Usage: check_e2_node.sh <e2_node_id>"
echo "E2 node IDs: 1 or 2"

namespace="ricplt"
echo "namespace=$namespace"

echo "----------------- Getting E2 node $1 logs -----------------"
kubectl logs POD/$(kubectl get pods -n $namespace | grep e2simid$1 | awk '{print $1}') -n $namespace