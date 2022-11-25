#!/bin/bash

ZONE="europe-central2-a"
INSTANCE_NAME="terraria-server"

echo "Stopping server instance..."
gcloud compute instances stop --zone=${ZONE} ${INSTANCE_NAME}
