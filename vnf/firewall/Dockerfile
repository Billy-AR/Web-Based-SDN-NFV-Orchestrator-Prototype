# vnf/firewall/Dockerfile
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    iptables \
    iproute2 \
    iputils-ping \
    tcpdump \
    iperf3 \
    && rm -rf /var/lib/apt/lists/*

# Basic script to start tailing so container doesn't exit
CMD ["tail", "-f", "/dev/null"]
