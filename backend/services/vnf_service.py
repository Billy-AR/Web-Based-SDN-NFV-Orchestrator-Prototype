import docker

class VNFService:
    VNF_CATALOG = {
        "fw": {
            "role": "firewall",
            "label": "Firewall",
            "image": "ubuntu:latest",
            "command": "tail -f /dev/null",
            "ip": "10.0.0.254",
        },
        "ids": {
            "role": "ids",
            "label": "IDS Sensor",
            "image": "ubuntu:latest",
            "command": "tail -f /dev/null",
            "ip": "10.0.0.253",
        },
        "lb": {
            "role": "load_balancer",
            "label": "Load Balancer",
            "image": "nginx:latest",
            "command": "nginx -g 'daemon off;'",
            "ip": "10.0.0.252",
        },
        "server": {
            "role": "server",
            "label": "Application Server",
            "image": "nginx:latest",
            "command": "nginx -g 'daemon off;'",
            "ip": "10.0.0.2",
        },
    }

    @staticmethod
    def get_client():
        try:
            return docker.from_env()
        except Exception as e:
            print(f"Docker connection error: {e}")
            return None

    @staticmethod
    def get_catalog():
        return VNFService.VNF_CATALOG

    @staticmethod
    def get_definition(vnf_name, role=None):
        if vnf_name in VNFService.VNF_CATALOG:
            return VNFService.VNF_CATALOG[vnf_name]

        for definition in VNFService.VNF_CATALOG.values():
            if definition["role"] == role:
                return definition

        return {
            "role": role or "firewall",
            "label": vnf_name.upper(),
            "image": "ubuntu:latest",
            "command": "tail -f /dev/null",
            "ip": "unknown",
        }

    @staticmethod
    def deploy_vnf(vnf_name, image="ubuntu:latest", role="firewall"):
        client = VNFService.get_client()
        if not client:
            return {"status": "error", "message": "Docker not available"}

        definition = VNFService.get_definition(vnf_name, role=role)
        image = definition["image"]
        cmd = definition["command"]
        role = definition["role"]
        
        try:
            # Check if exists
            try:
                container = client.containers.get(vnf_name)
                if container.status != 'running':
                    container.start()
                return {
                    "status": "success",
                    "message": f"{vnf_name} started.",
                    "id": container.id[:12],
                    "role": role,
                }
            except docker.errors.NotFound:
                pass
            
            # Start new container
            container = client.containers.run(
                image,
                name=vnf_name,
                detach=True,
                command=cmd,
                cap_add=["NET_ADMIN"],
                network_mode="bridge"
            )
            return {
                "status": "success",
                "message": f"{vnf_name} deployed successfully.",
                "id": container.id[:12],
                "role": role,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def stop_vnf(vnf_name):
        client = VNFService.get_client()
        if not client:
            return {"status": "error", "message": "Docker not available"}
        
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
        if not client:
            return []
        
        try:
            containers = client.containers.list(all=True)
            vnfs = []
            for c in containers:
                if c.name in VNFService.VNF_CATALOG:
                    definition = VNFService.get_definition(c.name)
                    vnfs.append({
                        "name": c.name,
                        "id": c.id[:12],
                        "short_id": c.id[:12],
                        "status": c.status,
                        "image": c.image.tags[0] if c.image.tags else "unknown",
                        "role": definition["role"],
                        "label": definition["label"],
                        "ip": definition["ip"],
                    })
            return vnfs
        except Exception as e:
            print(f"Error listing containers: {e}")
            return []

    @staticmethod
    def get_status_map():
        statuses = {name: {"status": "stopped", **definition} for name, definition in VNFService.VNF_CATALOG.items()}
        for container in VNFService.get_status():
            statuses[container["name"]] = container
        return statuses
