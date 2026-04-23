# vnf/server/Dockerfile
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    nginx \
    iproute2 \
    iputils-ping \
    iperf3 \
    && rm -rf /var/lib/apt/lists/*

# Start nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
