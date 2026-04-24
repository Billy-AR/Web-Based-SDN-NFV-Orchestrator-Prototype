import requests
from .controller_config import ControllerConfig

class RyuService:
    REQUEST_TIMEOUT = 3
    POLICY_PRIORITY = 500
    HOST_IPS = {
        "h1": "10.0.0.1",
        "h2": "10.0.0.2",
        "fw": "10.0.0.254",
        "ids": "10.0.0.253",
        "lb": "10.0.0.252",
    }
    PORT_MAP = {
        "h1": 1,
        "s2": 2,
        "fw": 3,
        "ids": 4,
        "lb": 5,
    }
    POLICY_CATALOG = {
        "direct": {
            "label": "Direct Path",
            "chain": [],
            "required_vnfs": [],
            "path": ["h1", "s1", "s2", "h2"],
            "description": "Route traffic directly from client to server.",
        },
        "firewall": {
            "label": "Firewall Inspection",
            "chain": ["fw"],
            "required_vnfs": ["fw"],
            "path": ["h1", "s1", "fw", "s1", "s2", "h2"],
            "description": "Send traffic through the Firewall VNF before the server.",
        },
        "ids": {
            "label": "IDS Mirror Chain",
            "chain": ["ids"],
            "required_vnfs": ["ids"],
            "path": ["h1", "s1", "ids", "s1", "s2", "h2"],
            "description": "Inspect traffic through the IDS VNF.",
        },
        "load_balancer": {
            "label": "Load Balancer Service",
            "chain": ["lb"],
            "required_vnfs": ["lb"],
            "path": ["h1", "s1", "lb", "s1", "s2", "h2"],
            "description": "Send traffic through the Load Balancer VNF.",
        },
        "firewall_then_ids": {
            "label": "Firewall + IDS Chain",
            "chain": ["fw", "ids"],
            "required_vnfs": ["fw", "ids"],
            "path": ["h1", "s1", "fw", "s1", "ids", "s1", "s2", "h2"],
            "description": "Sequentially inspect traffic through Firewall and IDS.",
        },
    }

    @staticmethod
    def get_config():
        return ControllerConfig.get()

    @staticmethod
    def _request(method, path, **kwargs):
        config = ControllerConfig.get()
        url = f"{config['rest_url']}{path}"
        return requests.request(method, url, timeout=RyuService.REQUEST_TIMEOUT, **kwargs)

    @staticmethod
    def get_status():
        config = ControllerConfig.get()
        try:
            response = RyuService._request("GET", "/stats/switches")
            if response.status_code == 200:
                return {
                    "active": True,
                    "switches": response.json(),
                    "config": config,
                }
        except requests.RequestException:
            pass

        return {
            "active": False,
            "switches": [],
            "config": config,
        }

    @staticmethod
    def get_switches():
        return RyuService.get_status()["switches"]

    @staticmethod
    def get_policy_catalog():
        catalog = []
        for key, definition in RyuService.POLICY_CATALOG.items():
            catalog.append({
                "key": key,
                **definition,
            })
        return catalog

    @staticmethod
    def get_flows(dpid=1):
        try:
            response = RyuService._request("GET", f"/stats/flow/{dpid}")
            if response.status_code == 200:
                return response.json().get(str(dpid), [])
            return []
        except requests.RequestException:
            return []

    @staticmethod
    def _normalize_match_key(key):
        aliases = {
            "eth_type": "dl_type",
            "dl_type": "dl_type",
        }
        return aliases.get(key, key)

    @staticmethod
    def _normalize_match_value(value):
        if isinstance(value, str) and value.endswith("/32"):
            return value[:-3]
        return value

    @staticmethod
    def _matches_flow_spec(flow, spec):
        flow_match = flow.get("match", {})
        expected_match = spec.get("match", {})

        for key, expected_value in expected_match.items():
            normalized_key = RyuService._normalize_match_key(key)
            actual_value = flow_match.get(normalized_key)
            if RyuService._normalize_match_value(actual_value) != RyuService._normalize_match_value(expected_value):
                return False

        return flow.get("priority") == spec.get("priority")

    @staticmethod
    def install_flow(dpid, match, actions, priority=100, cookie=10):
        # Format required by ofctl_rest
        payload = {
            "dpid": dpid,
            "cookie": cookie,
            "cookie_mask": cookie,
            "table_id": 0,
            "idle_timeout": 0,
            "hard_timeout": 0,
            "priority": priority,
            "flags": 1,
            "match": match,
            "actions": actions
        }
        
        try:
            response = RyuService._request("POST", "/stats/flowentry/add", json=payload)
            if response.status_code == 200:
                return {"status": "success", "message": "Flow installed successfully."}
            else:
                return {"status": "error", "message": f"Failed to install flow: {response.text}"}
        except requests.RequestException as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def delete_flow(dpid, match, priority=100):
        payload = {
            "dpid": dpid,
            "table_id": 0,
            "priority": priority,
            "match": match,
        }

        try:
            response = RyuService._request("POST", "/stats/flowentry/delete", json=payload)
            if response.status_code == 200:
                return {"status": "success"}
            return {"status": "error", "message": f"Failed to delete flow: {response.text}"}
        except requests.RequestException as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def _build_flow_specs(policy_key):
        host1 = RyuService.HOST_IPS["h1"]
        host2 = RyuService.HOST_IPS["h2"]
        ipv4_match = {
            "nw_src": f"{host1}/32",
            "nw_dst": f"{host2}/32",
            "eth_type": 2048,
        }

        if policy_key == "direct":
            return [{
                "dpid": 1,
                "priority": RyuService.POLICY_PRIORITY,
                "match": ipv4_match,
                "actions": [{"type": "OUTPUT", "port": RyuService.PORT_MAP["s2"]}],
                "stage": "direct-to-server",
            }]

        chain = RyuService.POLICY_CATALOG[policy_key]["chain"]
        specs = []

        first_hop = chain[0]
        specs.append({
            "dpid": 1,
            "priority": RyuService.POLICY_PRIORITY,
            "match": ipv4_match,
            "actions": [{"type": "OUTPUT", "port": RyuService.PORT_MAP[first_hop]}],
            "stage": f"h1-to-{first_hop}",
        })

        for current_vnf, next_vnf in zip(chain, chain[1:]):
            specs.append({
                "dpid": 1,
                "priority": RyuService.POLICY_PRIORITY + 1,
                "match": {
                    "in_port": RyuService.PORT_MAP[current_vnf],
                    "nw_dst": f"{host2}/32",
                    "eth_type": 2048,
                },
                "actions": [{"type": "OUTPUT", "port": RyuService.PORT_MAP[next_vnf]}],
                "stage": f"{current_vnf}-to-{next_vnf}",
            })

        last_vnf = chain[-1]
        specs.append({
            "dpid": 1,
            "priority": RyuService.POLICY_PRIORITY + 2,
            "match": {
                "in_port": RyuService.PORT_MAP[last_vnf],
                "nw_dst": f"{host2}/32",
                "eth_type": 2048,
            },
            "actions": [{"type": "OUTPUT", "port": RyuService.PORT_MAP["s2"]}],
            "stage": f"{last_vnf}-to-server",
        })

        return specs

    @staticmethod
    def clear_policy_flows():
        seen = set()
        for policy in RyuService.POLICY_CATALOG:
            for spec in RyuService._build_flow_specs(policy):
                key = (spec["dpid"], spec["priority"], tuple(sorted(spec["match"].items())))
                if key in seen:
                    continue
                seen.add(key)
                RyuService.delete_flow(spec["dpid"], spec["match"], priority=spec["priority"])

    @staticmethod
    def apply_chain_policy(policy_key):
        switches = RyuService.get_switches()
        if 1 not in switches:
            return {
                "status": "error",
                "message": "Switch s1 (dpid 1) is not connected to the SDN controller."
            }

        if policy_key not in RyuService.POLICY_CATALOG:
            return {"status": "error", "message": f"Unknown policy '{policy_key}'."}

        RyuService.clear_policy_flows()
        specs = RyuService._build_flow_specs(policy_key)
        results = []
        for spec in specs:
            result = RyuService.install_flow(
                spec["dpid"],
                spec["match"],
                spec["actions"],
                priority=spec["priority"],
            )
            results.append(result)

        errors = [result["message"] for result in results if result["status"] != "success"]
        if errors:
            detail = " | ".join(errors)
            return {"status": "error", "message": f"Failed to apply policy. {detail}"}

        label = RyuService.POLICY_CATALOG[policy_key]["label"]
        return {
            "status": "success",
            "message": f"Policy '{label}' applied successfully.",
            "flows": specs,
        }

    @staticmethod
    def get_policy_flow_snapshot(policy_key):
        if policy_key not in RyuService.POLICY_CATALOG:
            return {
                "packets": 0,
                "bytes": 0,
                "rules": [],
            }

        installed = RyuService.get_flows(1)
        rules = []
        total_packets = 0
        total_bytes = 0
        for spec in RyuService._build_flow_specs(policy_key):
            for flow in installed:
                if not RyuService._matches_flow_spec(flow, spec):
                    continue
                total_packets += flow.get("packet_count", 0)
                total_bytes += flow.get("byte_count", 0)
                rules.append(flow)
                break

        return {
            "packets": total_packets,
            "bytes": total_bytes,
            "rules": rules,
        }

    @staticmethod
    def redirect_traffic_to_firewall():
        return RyuService.apply_chain_policy("firewall")
