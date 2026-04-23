import psutil
from .topology_service import TopologyService
from .vnf_service import VNFService
from .ryu_service import RyuService
from .orchestrator_service import OrchestratorService

class MonitoringService:
    @staticmethod
    def get_all_stats():
        topo_status = TopologyService.get_status()
        vnfs = VNFService.get_status()
        controller_status = RyuService.get_status()
        controller_config = controller_status["config"]
        switches = controller_status["switches"]
        orchestrator_state = OrchestratorService.get_runtime_state()
        
        # Calculate active flows across switches
        total_flows = 0
        if switches:
            for dpid in switches:
                flows = RyuService.get_flows(dpid)
                total_flows += len(flows)
                
        # Get System Resources
        cpu_percent = psutil.cpu_percent(interval=None) # Non-blocking
        mem = psutil.virtual_memory()
        system_stats = {
            "cpu_percent": cpu_percent,
            "memory_percent": mem.percent,
            "memory_used_mb": round(mem.used / (1024 * 1024), 2),
            "memory_total_mb": round(mem.total / (1024 * 1024), 2)
        }
                
        return {
            "topology": topo_status,
            "vnfs": vnfs,
            "sdn_controller": {
                "active": controller_status["active"],
                "name": controller_config["name"],
                "mode": controller_config["mode"],
                "mode_label": controller_config["mode_label"],
                "host": controller_config["host"],
                "rest_api": controller_config["rest_api"],
                "openflow_endpoint": controller_config["openflow_endpoint"],
                "switches_connected": len(switches),
                "total_flows": total_flows
            },
            "system": system_stats,
            "orchestrator": orchestrator_state,
        }
