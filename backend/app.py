from flask import Flask, jsonify, request, render_template
from services.topology_service import TopologyService
from services.vnf_service import VNFService
from services.ryu_service import RyuService
from services.monitoring_service import MonitoringService
from services.orchestrator_service import OrchestratorService

app = Flask(__name__)


def render_dashboard(template_name, active_page, page_title, page_subtitle):
    return render_template(
        template_name,
        active_page=active_page,
        page_title=page_title,
        page_subtitle=page_subtitle,
        controller_config=RyuService.get_config(),
    )


@app.route('/')
def index():
    return render_dashboard(
        'overview.html',
        'overview',
        'Overview',
        'KPIs, path, and current state.',
    )


@app.route('/topology')
def topology_page():
    return render_dashboard(
        'topology.html',
        'topology',
        'Topology & Policy',
        'Fabric control, VNF deployment, and policy apply.',
    )


@app.route('/observability')
def observability_page():
    return render_dashboard(
        'observability.html',
        'observability',
        'Observability',
        'Traffic, incidents, playback, and log.',
    )


@app.route('/infrastructure')
def infrastructure_page():
    return render_dashboard(
        'infrastructure.html',
        'infrastructure',
        'Infrastructure',
        'Controller, resources, VNF fleet, and scenarios.',
    )

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
@app.route('/api/policies', methods=['GET'])
def get_policies():
    return jsonify(OrchestratorService.get_policy_catalog())

@app.route('/api/policy/apply', methods=['POST'])
def apply_policy():
    data = request.json or {}
    policy_key = data.get('policy', 'direct')
    auto_deploy = data.get('auto_deploy', True)
    result = OrchestratorService.apply_policy(policy_key, auto_deploy=auto_deploy, reason='manual')
    return jsonify(result)

@app.route('/api/flow/install', methods=['POST'])
def install_flow():
    data = request.json or {}
    policy_type = data.get('type')
    
    if policy_type == 'redirect_firewall':
        result = OrchestratorService.apply_policy('firewall', auto_deploy=True, reason='legacy_flow_api')
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
@app.route('/api/telemetry', methods=['GET'])
def get_telemetry():
    return jsonify(OrchestratorService.get_runtime_state())

@app.route('/api/scenario/trigger', methods=['POST'])
def trigger_scenario():
    data = request.json or {}
    scenario_key = data.get('scenario')
    if not scenario_key:
        return jsonify({"status": "error", "message": "Missing scenario name"})
    return jsonify(OrchestratorService.trigger_scenario(scenario_key, options=data))

@app.route('/api/stats', methods=['GET'])
def get_stats():
    stats = MonitoringService.get_all_stats()
    return jsonify(stats)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
