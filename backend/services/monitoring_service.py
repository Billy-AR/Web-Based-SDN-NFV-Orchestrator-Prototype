import psutil
from .topology_service import TopologyService
from .vnf_service import VNFService
from .ryu_service import RyuService

class MonitoringService:
    @staticmethod
    def get_all_stats():
        topo_status = TopologyService.get_status()
        vnfs = VNFService.get_status()
        switches = RyuService.get_switches()
        
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
                "active": len(switches) > 0,
                "switches_connected": len(switches),
                "total_flows": total_flows
            },
            "system": system_stats
        }
