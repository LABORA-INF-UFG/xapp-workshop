#!/bin/bash
echo "Usage: unregister_xapp.sh <xappname>"
xappname=$1
curl -X POST http://$(kubectl get pods -n ricplt -o wide | grep appmgr | awk '{print $6}'):8080/ric/v1/deregister -H "Content-Type: application/json" -d "{\"appName\": \"${xappname}\", \"appInstanceName\": \"${xappname}\"}"
echo "Registered xApps:"
curl -X GET http://$(kubectl get pods -n ricplt -o wide | grep appmgr | awk '{print $6}'):8080/ric/v1/xapps | jq