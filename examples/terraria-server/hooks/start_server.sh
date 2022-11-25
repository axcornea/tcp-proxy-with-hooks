#!/bin/bash

ZONE="europe-central2-a"
INSTANCE_NAME="terraria-server"

echo "Starting server instance..."
gcloud compute instances start --zone=${ZONE} ${INSTANCE_NAME}

echo "Waiting 30secs for server to start."
sleep 30
