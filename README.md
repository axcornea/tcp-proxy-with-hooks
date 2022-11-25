# Wake up VMs by TCP requests

This simple tool supports setups where you have an expensive server (VM) that is running 24/7, but actually serves requests only at some period of time, and scheduled boot policies doesn't work. It is designed for the TCP applications like legacy server apps, game servers, anm others.

> If you have an HTTP application that you want to be auto started/stopped based on HTTP requests - _GCP AppEngine_ or a similar service will do a better job.

# Design

This tool is a TCP proxy server that intercepts all requests to your _target_ server. In case if the server is not reachable - it tries first to start the target server using the "start" hook (a script provided by the end user, dependend on their specific use cases). If server successfully starts - it forwards all the traffic between client and the target. After all the clients have disconnected, it waits for a period of time and then shuts down the target server using another - "stop" hook script.

Below are the diagrams with a visual representation of this process.

### Case 1. Target server is alive when request arrives

<img src="docs/proxy_arch_when_target_alive.png" style="height: 300px">

### Case 2. Target server is dead when request arrives

<img src="docs/proxy_arch_when_target_dead.png" style="height: 300px">

# How to set up

> Assuming your application server is running at address `192.168.100.15` at port `:8000`.

### 1. Create your `start` and `stop` hook

Start hook is a script that starts your application. In example, it can spin up a Docker container, or make a call to the cloud platform to start a VM. Take a look at the provided examples in the `examples/` folder.

For the next steps let's assume they are located in the same directory and named `start.sh` and `stop.sh`.

### 2. Run proxy server

Here we are demonstrating how to run it locally, but usually it is better to wrap it into a systemd or other service supervisor.

```bash
server.py \
    --target-ip=192.168.100.15 \
    --target-port=8000 \
    --hook-start-svc=./start.sh \
    --hook-stop-svc=./stop.sh \
    --cooldown-period=60
```

That's all, it is running.

# Things to consider

## Throughput

Due to the design and simplicity of this tool, it doesn't provide a high throughput, however it should be enough to serve in most cases.

## Target graceful shut down

Due to the aggressive nature of the process and ignorance of the "business logic" of specific cases, you as developer or maintainer might want to make sure that your target application is configured to shut down gracefully during the standard OS shut down procedure. Loosing your data is definitely not what you want. 

## Costs

Depending on the platform where you deploy this setup, you might have additional costs for the time VM is stopped and not terminated. Consult documentation of your cloud platform for more details.
