import requests
import json

class RyuService:
    BASE_URL = "http://127.0.0.1:8080" # Default port for ofctl_rest

    @staticmethod
    def get_switches():
        try:
            response = requests.get(f"{RyuService.BASE_URL}/stats/switches")
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            return []

    @staticmethod
    def get_flows(dpid=1):
        try:
            response = requests.get(f"{RyuService.BASE_URL}/stats/flow/{dpid}")
            if response.status_code == 200:
                return response.json().get(str(dpid), [])
            return []
        except Exception as e:
            return []

    @staticmethod
    def install_flow(dpid, match, actions, priority=100):
        url = f"{RyuService.BASE_URL}/stats/flowentry/add"
        
        # Format required by ofctl_rest
        payload = {
            "dpid": dpid,
            "cookie": 1,
            "cookie_mask": 1,
            "table_id": 0,
            "idle_timeout": 0,
            "hard_timeout": 0,
            "priority": priority,
            "flags": 1,
            "match": match,
            "actions": actions
        }
        
        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                return {"status": "success", "message": "Flow installed successfully."}
            else:
                return {"status": "error", "message": f"Failed to install flow: {response.text}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def redirect_traffic_to_firewall():
        # Example policy: Redirect h1 (10.0.0.1) -> h2 (10.0.0.2) traffic to fw (10.0.0.254) on switch s1 (dpid 1)
        # Assuming: 
        # s1 port 1 is h1
        # s1 port 2 is s2
        # s1 port 3 is fw
        
        # Rule 1: h1 to h2 goes to port 3 (fw) instead of port 2
        match1 = {
            "nw_src": "10.0.0.1/32",
            "nw_dst": "10.0.0.2/32",
            "eth_type": 2048 # IPv4
        }
        actions1 = [
            {"type": "OUTPUT", "port": 3}
        ]
        res1 = RyuService.install_flow(1, match1, actions1, priority=500)
        
        # Rule 2: from fw to h2 goes out port 2
        match2 = {
            "in_port": 3,
            "nw_dst": "10.0.0.2/32",
            "eth_type": 2048
        }
        actions2 = [
            {"type": "OUTPUT", "port": 2}
        ]
        res2 = RyuService.install_flow(1, match2, actions2, priority=500)
        
        if res1['status'] == 'success' and res2['status'] == 'success':
            return {"status": "success", "message": "Policy 'Redirect to Firewall' applied successfully."}
        else:
            return {"status": "error", "message": "Failed to apply redirect policy."}
