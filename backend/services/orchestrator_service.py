from collections import deque
from copy import deepcopy
from datetime import datetime, timezone

from .ryu_service import RyuService
from .vnf_service import VNFService


class OrchestratorService:
    _events = deque(maxlen=80)
    _incidents = deque(maxlen=20)
    _event_seq = 0
    _incident_seq = 0
    _active_policy = None
    _desired_policy = None
    _last_health_issue = None

    @staticmethod
    def _now():
        now = datetime.now(timezone.utc)
        return {
            "iso": now.isoformat(),
            "label": now.strftime("%H:%M:%S"),
        }

    @classmethod
    def log_event(cls, message, level="info", category="system", details=None):
        stamp = cls._now()
        cls._event_seq += 1
        event = {
            "id": cls._event_seq,
            "message": message,
            "level": level,
            "category": category,
            "timestamp": stamp["iso"],
            "time_label": stamp["label"],
            "details": details or {},
        }
        cls._events.append(event)
        return event

    @classmethod
    def record_incident(cls, title, severity="warning", details=None):
        stamp = cls._now()
        cls._incident_seq += 1
        incident = {
            "id": cls._incident_seq,
            "title": title,
            "severity": severity,
            "timestamp": stamp["iso"],
            "time_label": stamp["label"],
            "details": details or {},
        }
        cls._incidents.appendleft(incident)
        return incident

    @classmethod
    def get_policy_catalog(cls):
        return RyuService.get_policy_catalog()

    @classmethod
    def _build_policy_state(cls, policy_key, reason="manual", status="active", fallback_from=None):
        catalog = {policy["key"]: policy for policy in cls.get_policy_catalog()}
        policy = catalog[policy_key]
        stamp = cls._now()
        return {
            "key": policy_key,
            "label": policy["label"],
            "chain": policy["chain"],
            "required_vnfs": policy["required_vnfs"],
            "path": policy["path"],
            "description": policy["description"],
            "status": status,
            "reason": reason,
            "fallback_from": fallback_from,
            "installed_at": stamp["iso"],
            "installed_label": stamp["label"],
        }

    @classmethod
    def _get_node_status(cls):
        statuses = VNFService.get_status_map()
        return {
            name: {
                "status": statuses.get(name, {}).get("status", "stopped"),
                "label": statuses.get(name, {}).get("label", name.upper()),
                "role": statuses.get(name, {}).get("role", name),
                "ip": statuses.get(name, {}).get("ip", "unknown"),
            }
            for name in ["fw", "ids", "lb"]
        }

    @classmethod
    def _get_traffic_metrics(cls):
        if not cls._active_policy:
            return {
                "packets": 0,
                "bytes": 0,
                "rule_count": 0,
                "active_path": ["h1", "s1", "s2", "h2"],
            }

        snapshot = RyuService.get_policy_flow_snapshot(cls._active_policy["key"])
        return {
            "packets": snapshot["packets"],
            "bytes": snapshot["bytes"],
            "rule_count": len(snapshot["rules"]),
            "active_path": cls._active_policy["path"],
        }

    @classmethod
    def get_runtime_state(cls):
        cls.evaluate_health()
        traffic = cls._get_traffic_metrics()
        node_status = cls._get_node_status()
        return {
            "catalog": cls.get_policy_catalog(),
            "active_policy": deepcopy(cls._active_policy),
            "desired_policy": deepcopy(cls._desired_policy),
            "events": list(cls._events),
            "incidents": list(cls._incidents),
            "telemetry": {
                "traffic": traffic,
                "node_status": node_status,
                "health": cls._active_policy["status"] if cls._active_policy else "idle",
            },
        }

    @classmethod
    def apply_policy(cls, policy_key, auto_deploy=True, reason="manual"):
        catalog = {policy["key"]: policy for policy in cls.get_policy_catalog()}
        if policy_key not in catalog:
            return {"status": "error", "message": f"Unknown policy '{policy_key}'."}

        policy = catalog[policy_key]
        deployments = []

        if 1 not in RyuService.get_switches():
            return {
                "status": "error",
                "message": "Switch s1 (dpid 1) is not connected to the SDN controller.",
            }

        if auto_deploy:
            for vnf_name in policy["required_vnfs"]:
                deployment = VNFService.deploy_vnf(vnf_name)
                deployments.append(deployment)
                if deployment["status"] != "success":
                    cls.log_event(
                        f"Failed to auto-deploy {vnf_name}: {deployment['message']}",
                        level="error",
                        category="vnf",
                    )
                    return {
                        "status": "error",
                        "message": f"Failed to prepare VNF '{vnf_name}'. {deployment['message']}",
                    }

        result = RyuService.apply_chain_policy(policy_key)
        if result["status"] != "success":
            cls.log_event(result["message"], level="error", category="policy")
            return result

        cls._active_policy = cls._build_policy_state(policy_key, reason=reason, status="active")
        cls._desired_policy = deepcopy(cls._active_policy)
        cls._last_health_issue = None

        if deployments:
            deployed_names = ", ".join(
                deployment.get("role", deployment.get("message", "VNF")).replace("_", " ")
                for deployment in deployments
            )
            cls.log_event(
                f"Policy '{cls._active_policy['label']}' auto-prepared VNFs: {deployed_names}.",
                level="info",
                category="vnf",
            )

        cls.log_event(
            f"Policy '{cls._active_policy['label']}' applied with path: {' -> '.join(cls._active_policy['path'])}.",
            level="success",
            category="policy",
        )

        return {
            "status": "success",
            "message": result["message"],
            "policy": deepcopy(cls._active_policy),
            "deployments": deployments,
        }

    @classmethod
    def fallback_to_direct(cls, reason="manual fallback", preserve_desired=True):
        fallback_from = cls._active_policy["label"] if cls._active_policy else None
        result = RyuService.apply_chain_policy("direct")
        if result["status"] != "success":
            cls.log_event(result["message"], level="error", category="healing")
            return result

        if preserve_desired and cls._desired_policy is None and cls._active_policy:
            cls._desired_policy = deepcopy(cls._active_policy)

        cls._active_policy = cls._build_policy_state(
            "direct",
            reason=reason,
            status="fallback",
            fallback_from=fallback_from,
        )
        cls.log_event(
            f"Direct fallback activated. Previous chain: {fallback_from or 'none'}.",
            level="warning",
            category="healing",
        )
        return {
            "status": "success",
            "message": "Direct fallback activated successfully.",
            "policy": deepcopy(cls._active_policy),
        }

    @classmethod
    def evaluate_health(cls):
        if not cls._active_policy:
            return

        required_vnfs = cls._active_policy.get("required_vnfs", [])
        if not required_vnfs:
            cls._last_health_issue = None
            return

        statuses = cls._get_node_status()
        missing = [vnf for vnf in required_vnfs if statuses.get(vnf, {}).get("status") != "running"]
        if not missing:
            cls._last_health_issue = None
            return

        issue_signature = f"missing:{','.join(sorted(missing))}"
        if issue_signature == cls._last_health_issue:
            return

        cls._last_health_issue = issue_signature
        cls.record_incident(
            f"Required VNF down: {', '.join(missing)}",
            severity="critical",
            details={"missing_vnfs": missing},
        )
        cls.log_event(
            f"Detected VNF failure on active chain: {', '.join(missing)}.",
            level="error",
            category="healing",
        )
        cls.fallback_to_direct(reason=f"auto-fallback because {', '.join(missing)} is down")

    @classmethod
    def trigger_scenario(cls, scenario_key):
        if scenario_key == "kill_active_vnf":
            policy = cls._active_policy or cls._desired_policy
            if not policy or not policy.get("required_vnfs"):
                return {
                    "status": "error",
                    "message": "No active service chain with VNFs is available for failure injection.",
                }
            target = policy["required_vnfs"][0]
            stop_result = VNFService.stop_vnf(target)
            if stop_result["status"] != "success":
                return stop_result
            cls.record_incident(
                f"Scenario injected: {target} terminated",
                severity="warning",
                details={"scenario": scenario_key, "target": target},
            )
            cls.log_event(
                f"Scenario '{scenario_key}' stopped VNF '{target}'.",
                level="warning",
                category="scenario",
            )
            cls.evaluate_health()
            return {
                "status": "success",
                "message": f"Scenario executed: {target} stopped and health check triggered.",
            }

        if scenario_key == "fallback_direct":
            return cls.fallback_to_direct(reason="manual scenario fallback")

        if scenario_key == "recover_policy":
            if not cls._desired_policy or cls._desired_policy["key"] == "direct":
                return {
                    "status": "error",
                    "message": "No previous chained policy is available for recovery.",
                }
            cls.log_event(
                f"Scenario 'recover_policy' restoring '{cls._desired_policy['label']}'.",
                level="info",
                category="scenario",
            )
            return cls.apply_policy(cls._desired_policy["key"], auto_deploy=True, reason="recovery")

        return {"status": "error", "message": f"Unknown scenario '{scenario_key}'."}
