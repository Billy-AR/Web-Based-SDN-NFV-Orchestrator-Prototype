#!/usr/bin/env python3
# mininet/topo.py

import os
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

RUNTIME_DIR_ENV = 'ORCHESTRATOR_RUNTIME_DIR'
DEFAULT_RUNTIME_DIR = os.path.join(
    '/tmp',
    f'web-sdn-nfv-orchestrator-uid-{os.getuid()}'
)


def _get_runtime_dir():
    return os.getenv(RUNTIME_DIR_ENV, DEFAULT_RUNTIME_DIR)


STATUS_FILE = os.path.join(_get_runtime_dir(), 'mininet_status.txt')

def _env_int(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default

def get_controller_config():
    mode = (os.getenv('SDN_CONTROLLER_MODE', 'local') or 'local').strip().lower()
    if mode not in {'local', 'docker'}:
        mode = 'local'

    host = (os.getenv('SDN_CONTROLLER_HOST', '127.0.0.1') or '').strip() or '127.0.0.1'
    port = _env_int('SDN_CONTROLLER_OF_PORT', 6653)

    return {
        'mode': mode,
        'mode_label': 'Docker' if mode == 'docker' else 'Local',
        'host': host,
        'port': port,
    }

def is_ryu_available(host, port, timeout=2):
    """Check if Ryu controller is reachable before starting."""
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True
    except (ConnectionRefusedError, socket.timeout, OSError):
        return False

def create_topology():
    os.makedirs(_get_runtime_dir(), mode=0o700, exist_ok=True)

    # Decide which controller to use
    controller_config = get_controller_config()
    ryu_available = is_ryu_available(controller_config['host'], controller_config['port'])

    if USE_CONTAINERNET:
        net = Containernet(switch=OVSKernelSwitch)
    else:
        net = Mininet(switch=OVSKernelSwitch)

    info('*** Adding controller\n')
    if ryu_available:
        info(
            f"*** {controller_config['mode_label']} Ryu controller detected at "
            f"{controller_config['host']}:{controller_config['port']}\n"
        )
        c0 = net.addController(
            'c0',
            controller=RemoteController,
            ip=controller_config['host'],
            port=controller_config['port']
        )
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
    ids = net.addHost('ids', ip='10.0.0.253/24', mac='00:00:00:00:00:FD')
    lb = net.addHost('lb', ip='10.0.0.252/24', mac='00:00:00:00:00:FC')

    info('*** Creating links\n')
    net.addLink(h1, s1)
    net.addLink(s1, s2)
    net.addLink(s2, h2)
    net.addLink(s1, fw)
    net.addLink(s1, ids)
    net.addLink(s1, lb)

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
        if ryu_available:
            f.write(f"Controller: Ryu ({controller_config['mode_label']})\n")
            f.write(f"Controller Endpoint: {controller_config['host']}:{controller_config['port']}\n")
        else:
            f.write("Controller: OVSController (Fallback)\n")
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
