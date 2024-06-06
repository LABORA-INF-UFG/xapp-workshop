#!/bin/bash

echo "----------------- Restarting e2simid1 and e2simid2 -----------------"
kubectl -n ricplt delete pods \
$(kubectl get pods -n ricplt -o wide | grep e2simid2 | awk '{print $1}') \
$(kubectl get pods -n ricplt -o wide | grep submgr | awk '{print $1}') \
$(kubectl get pods -n ricplt -o wide | grep rtmgr | awk '{print $1}') \
$(kubectl get pods -n ricplt -o wide | grep e2mgr | awk '{print $1}') \
$(kubectl get pods -n ricplt -o wide | grep appmgr | awk '{print $1}') \
$(kubectl get pods -n ricplt -o wide | grep e2simid1 | awk '{print $1}')
