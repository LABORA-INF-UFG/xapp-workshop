#!/bin/bash

echo "----------------- Checking registry images -----------------"
curl -X GET http://127.0.0.1:5001/v2/_catalog
echo ""