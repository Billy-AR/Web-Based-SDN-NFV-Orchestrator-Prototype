import os
import subprocess
import time
import signal

PID_FILE = '/tmp/mininet_topo.pid'
STATUS_FILE = '/tmp/mininet_status.txt'
_topology_starting = False  # Lock flag


def _safe_cleanup():
    """
    Clean up Mininet leftovers WITHOUT killing the Ryu controller.
    
    The standard 'mn -c' command kills ALL OpenFlow-related processes,
    including Ryu. Instead, we manually clean up only the OVS bridges
    and network namespaces that Mininet created.
    """
    # Delete OVS bridges created by Mininet (s1, s2, etc.)
    try:
        result = subprocess.run(
            ["ovs-vsctl", "list-br"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            for br in result.stdout.strip().split('\n'):
                br = br.strip()
                if br:
                    subprocess.run(
                        ["ovs-vsctl", "--if-exists", "del-br", br],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5
                    )
    except Exception:
        pass

    # Clean up Mininet network namespaces
    try:
        result = subprocess.run(
            ["ip", "netns", "list"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            for ns in result.stdout.strip().split('\n'):
                ns = ns.strip().split()[0] if ns.strip() else ''
                if ns:
                    subprocess.run(
                        ["ip", "netns", "delete", ns],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5
                    )
    except Exception:
        pass

    # Clean up leftover veth interfaces
    try:
        result = subprocess.run(
            ["ip", "link", "show"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                for prefix in ['s1-', 's2-', 'h1-', 'h2-', 'fw-']:
                    if prefix in line:
                        iface = line.split(':')[1].strip().split('@')[0] if ':' in line else ''
                        if iface:
                            subprocess.run(
                                ["ip", "link", "delete", iface],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5
                            )
    except Exception:
        pass


class TopologyService:

    @staticmethod
    def start_topology():
        global _topology_starting
        if _topology_starting:
            return {"status": "error", "message": "Topology is already starting, please wait..."}
        _topology_starting = True
        try:
            # Kill any existing topo.py instance first
            TopologyService._kill_existing()

            # Safe cleanup (does NOT kill Ryu)
            _safe_cleanup()
            time.sleep(1)

            topo_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), '../../mininet/topo.py')
            )

            # Launch topo.py as a background process (detached)
            log_file = open('/tmp/mininet_topo.log', 'w')
            proc = subprocess.Popen(
                ["python3", topo_path],
                stdout=log_file,
                stderr=log_file,
                preexec_fn=os.setsid  # detach from parent process group
            )

            # Save PID so we can track it later
            with open(PID_FILE, 'w') as f:
                f.write(str(proc.pid))

            # Wait a moment and verify it's actually still running
            time.sleep(3)
            if proc.poll() is not None:
                # Process already exited - read the log for the error
                log_file.close()
                with open('/tmp/mininet_topo.log', 'r') as lf:
                    log_content = lf.read()[-500:]
                _topology_starting = False
                return {"status": "error", "message": f"Topology crashed on startup. Log: {log_content}"}

            log_file.close()
            _topology_starting = False
            return {"status": "success", "message": "Topology started successfully."}

        except Exception as e:
            _topology_starting = False
            return {"status": "error", "message": str(e)}

    @staticmethod
    def stop_topology():
        try:
            TopologyService._kill_existing()
            time.sleep(1)
            _safe_cleanup()

            for f in [PID_FILE, STATUS_FILE]:
                if os.path.exists(f):
                    os.remove(f)

            return {"status": "success", "message": "Topology stopped and cleaned."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def get_status():
        try:
            if not os.path.exists(PID_FILE):
                return {"status": "Stopped", "details": {}}

            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())

            # Check if the process is actually alive
            try:
                os.kill(pid, 0)  # Signal 0 = just check existence
                status = "Running"
            except ProcessLookupError:
                status = "Stopped"
                try:
                    os.remove(PID_FILE)
                except Exception:
                    pass
            except PermissionError:
                # PermissionError means the process EXISTS but we can't signal it
                # It's RUNNING
                status = "Running"

            details = {}
            if os.path.exists(STATUS_FILE):
                with open(STATUS_FILE, 'r') as f:
                    for line in f.readlines()[1:]:
                        if ':' in line:
                            k, v = line.split(':', 1)
                            details[k.strip()] = v.strip()

            return {"status": status, "details": details}
        except Exception as e:
            return {"status": "Stopped", "details": {}}

    @staticmethod
    def _kill_existing():
        """Kill any previously running topo.py process by its specific PID only."""
        if not os.path.exists(PID_FILE):
            return
        try:
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            os.kill(pid, signal.SIGTERM)
            time.sleep(1)
        except (ProcessLookupError, PermissionError):
            pass
        except Exception:
            pass
        try:
            os.remove(PID_FILE)
        except Exception:
            pass
