#!/usr/bin/env python3
# mininet/topo.py

import sys
import time
from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch, OVSController
from mininet.log import setLogLevel, info
import socket

try:
    from containernet.net import Containernet
    from containernet.node import Docker
    USE_CONTAINERNET = True
except ImportError:
    USE_CONTAINERNET = False

STATUS_FILE = '/tmp/mininet_status.txt'

def is_ryu_available(host='127.0.0.1', port=6653, timeout=2):
    """Check if Ryu controller is reachable before starting."""
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True
    except (ConnectionRefusedError, socket.timeout, OSError):
        return False

def create_topology():
    # Decide which controller to use
    ryu_available = is_ryu_available()

    if USE_CONTAINERNET:
        net = Containernet(switch=OVSKernelSwitch)
    else:
        net = Mininet(switch=OVSKernelSwitch)

    info('*** Adding controller\n')
    if ryu_available:
        info('*** Ryu Controller detected at 127.0.0.1:6653\n')
        c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6653)
    else:
        info('*** Ryu not detected. Switches will run in standalone (self-learning) mode.\n')
        c0 = None  # No controller needed in standalone mode

    info('*** Adding switches\n')
    # failMode='standalone' makes OVS act as a self-learning L2 switch without any controller
    s1 = net.addSwitch('s1', failMode='standalone')
    s2 = net.addSwitch('s2', failMode='standalone')


    info('*** Adding hosts\n')
    h1 = net.addHost('h1', ip='10.0.0.1/24', mac='00:00:00:00:00:01')
    h2 = net.addHost('h2', ip='10.0.0.2/24', mac='00:00:00:00:00:02')
    fw = net.addHost('fw', ip='10.0.0.254/24', mac='00:00:00:00:00:FE')

    info('*** Creating links\n')
    net.addLink(h1, s1)
    net.addLink(s1, s2)
    net.addLink(s2, h2)
    net.addLink(s1, fw)  # Firewall attached to s1

    info('*** Starting network\n')
    net.start()

    time.sleep(2)

    # Test connectivity (non-fatal)
    info('*** Testing basic connectivity (may fail without controller)\n')
    try:
        result = net.pingAll()
        info(f'*** Ping result: {result}% packet loss\n')
    except Exception as e:
        info(f'*** Ping test skipped: {e}\n')

    # Write status file so Flask backend can read it
    with open(STATUS_FILE, 'w') as f:
        f.write("RUNNING\n")
        f.write(f"Hosts: {len(net.hosts)}\n")
        f.write(f"Switches: {len(net.switches)}\n")
        f.write(f"Controller: {'Ryu (Remote)' if ryu_available else 'OVSController (Fallback)'}\n")
        f.write(f"Containernet: {USE_CONTAINERNET}\n")

    info('*** Topology is UP. Waiting for stop signal (press Ctrl+C or use Stop button)...\n')
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

    info('*** Stopping network\n')
    net.stop()

    with open(STATUS_FILE, 'w') as f:
        f.write("STOPPED\n")

if __name__ == '__main__':
    setLogLevel('info')
    create_topology()

