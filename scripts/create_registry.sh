#!/bin/bash

echo "----------------- Creating a local docker registry -----------------"
docker run -d -p 5001:5000 --restart unless-stopped --name registry registry:2
echo "Docker registry available at port 5001"
