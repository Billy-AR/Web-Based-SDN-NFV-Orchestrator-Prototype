import os

try:
    import docker
except Exception:
    docker = None


class ControllerConfig:
    DEFAULT_NAME = "Ryu OpenFlow 1.3"
    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_REST_PORT = 8080
    DEFAULT_OPENFLOW_PORT = 6653
    DOCKER_CONTROLLER_NAME = "sdn-ryu-controller"

    @staticmethod
    def _get_int(name, default):
        try:
            return int(os.getenv(name, str(default)))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _detect_mode():
        explicit_mode = (os.getenv("SDN_CONTROLLER_MODE", "") or "").strip().lower()
        if explicit_mode in {"local", "docker"}:
            return explicit_mode

        if docker is None:
            return "local"

        try:
            client = docker.from_env()
            container = client.containers.get(ControllerConfig.DOCKER_CONTROLLER_NAME)
            if container.status == "running":
                return "docker"
        except Exception:
            pass

        return "local"

    @staticmethod
    def get():
        mode = ControllerConfig._detect_mode()

        host = (os.getenv("SDN_CONTROLLER_HOST", ControllerConfig.DEFAULT_HOST) or "").strip()
        if not host:
            host = ControllerConfig.DEFAULT_HOST

        rest_port = ControllerConfig._get_int(
            "SDN_CONTROLLER_REST_PORT",
            ControllerConfig.DEFAULT_REST_PORT
        )
        openflow_port = ControllerConfig._get_int(
            "SDN_CONTROLLER_OF_PORT",
            ControllerConfig.DEFAULT_OPENFLOW_PORT
        )
        name = (os.getenv("SDN_CONTROLLER_NAME", ControllerConfig.DEFAULT_NAME) or "").strip()
        if not name:
            name = ControllerConfig.DEFAULT_NAME

        return {
            "name": name,
            "mode": mode,
            "mode_label": "Docker" if mode == "docker" else "Local",
            "host": host,
            "rest_port": rest_port,
            "openflow_port": openflow_port,
            "rest_api": f"{host}:{rest_port}",
            "openflow_endpoint": f"{host}:{openflow_port}",
            "rest_url": f"http://{host}:{rest_port}",
        }
