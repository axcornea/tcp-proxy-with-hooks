#!/bin/bash

python3 ./server.py \
	--proxy-port=7777 \
	--target-ip=${TARGET_IP} \
	--target-port=7777 \
	--cooldown-period=15 \
	--hook-start-svc=hooks/start_server.sh \
	--hook-stop-svc=hooks/stop_server.sh
