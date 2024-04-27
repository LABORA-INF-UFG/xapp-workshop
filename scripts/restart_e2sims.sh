#!/bin/bash

echo "----------------- Restarting e2simid1 and e2simid2 -----------------"
kubectl -n ricplt delete pod $(kubectl get pods -n ricplt -o wide | grep e2simid1 | awk '{print $1}')
kubectl -n ricplt delete pod $(kubectl get pods -n ricplt -o wide | grep e2simid2 | awk '{print $1}')
