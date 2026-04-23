import docker

class VNFService:
    @staticmethod
    def get_client():
        try:
            return docker.from_env()
        except Exception as e:
            print(f"Docker connection error: {e}")
            return None

    @staticmethod
    def deploy_vnf(vnf_name, image="ubuntu:latest", role="firewall"):
        client = VNFService.get_client()
        if not client: return {"status": "error", "message": "Docker not available"}
        
        try:
            # Check if exists
            try:
                container = client.containers.get(vnf_name)
                if container.status != 'running':
                    container.start()
                return {"status": "success", "message": f"{vnf_name} started."}
            except docker.errors.NotFound:
                pass
            
            # Start new container
            cmd = "tail -f /dev/null" if role == "firewall" else "nginx -g 'daemon off;'"
            if role == "server":
                image = "nginx:latest" # Use nginx directly for server if not using custom build
                
            container = client.containers.run(
                image,
                name=vnf_name,
                detach=True,
                command=cmd,
                cap_add=["NET_ADMIN"], # Needed for iptables
                network_mode="bridge" # Will be connected to OVS by Mininet or manually
            )
            return {"status": "success", "message": f"{vnf_name} deployed successfully.", "id": container.id[:12]}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def stop_vnf(vnf_name):
        client = VNFService.get_client()
        if not client: return {"status": "error", "message": "Docker not available"}
        
        try:
            container = client.containers.get(vnf_name)
            container.stop()
            container.remove()
            return {"status": "success", "message": f"{vnf_name} stopped and removed."}
        except docker.errors.NotFound:
            return {"status": "error", "message": f"{vnf_name} not found."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def get_status():
        client = VNFService.get_client()
        if not client: return []
        
        try:
            containers = client.containers.list(all=True)
            # Filter just ours or show all for prototype
            vnfs = []
            for c in containers:
                if c.name in ['fw', 'server', 'h2']:
                    vnfs.append({
                        "name": c.name,
                        "id": c.id[:12],
                        "status": c.status,
                        "image": c.image.tags[0] if c.image.tags else "unknown"
                    })
            return vnfs
        except Exception as e:
            print(f"Error listing containers: {e}")
            return []
