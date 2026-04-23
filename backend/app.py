from flask import Flask, jsonify, request, render_template
from services.topology_service import TopologyService
from services.vnf_service import VNFService
from services.ryu_service import RyuService
from services.monitoring_service import MonitoringService

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

# Topology API
@app.route('/api/topology/start', methods=['POST'])
def start_topology():
    result = TopologyService.start_topology()
    return jsonify(result)

@app.route('/api/topology/stop', methods=['POST'])
def stop_topology():
    result = TopologyService.stop_topology()
    return jsonify(result)

# VNF API
@app.route('/api/vnf/deploy', methods=['POST'])
def deploy_vnf():
    data = request.json or {}
    vnf_name = data.get('name', 'fw')
    role = data.get('role', 'firewall')
    result = VNFService.deploy_vnf(vnf_name, role=role)
    return jsonify(result)

@app.route('/api/vnf/stop', methods=['POST'])
def stop_vnf():
    data = request.json or {}
    vnf_name = data.get('name')
    if not vnf_name:
        return jsonify({"status": "error", "message": "Missing VNF name"})
    result = VNFService.stop_vnf(vnf_name)
    return jsonify(result)

# SDN Policy API
@app.route('/api/flow/install', methods=['POST'])
def install_flow():
    data = request.json or {}
    policy_type = data.get('type')
    
    if policy_type == 'redirect_firewall':
        result = RyuService.redirect_traffic_to_firewall()
        return jsonify(result)
    else:
        return jsonify({"status": "error", "message": "Unknown policy type"})

@app.route('/api/flow/details', methods=['GET'])
def get_flow_details():
    switches = RyuService.get_switches()
    all_flows = {}
    if switches:
        for dpid in switches:
            all_flows[f"Switch_{dpid}"] = RyuService.get_flows(dpid)
    return jsonify(all_flows)

# Monitoring API
@app.route('/api/stats', methods=['GET'])
def get_stats():
    stats = MonitoringService.get_all_stats()
    return jsonify(stats)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
