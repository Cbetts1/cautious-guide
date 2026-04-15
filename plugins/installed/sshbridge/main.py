"""
AIOS Plugin: sshbridge
SSH tunnel bridge. Checks for openssh availability, manages tunnel config,
starts/stops SSH tunnels. Falls back gracefully when ssh is not installed.
"""

import os
import sys
import json
import subprocess
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

PLUGIN_NAME    = "sshbridge"
PLUGIN_VERSION = "1.0.0"
CFG_PATH       = os.path.expanduser("~/.aios/sshbridge.json")

_tunnel_proc = None
_lock        = threading.Lock()

DEFAULT_CFG = {
    "remote_host": "",
    "remote_user": "",
    "remote_port": 22,
    "local_port":  2222,
    "identity":    "",
    "extra_args":  [],
}


def _has_ssh() -> bool:
    try:
        r = subprocess.run(["ssh", "-V"], capture_output=True, timeout=3)
        return r.returncode == 0 or b"OpenSSH" in (r.stderr or b"")
    except Exception:
        return False


def _load_cfg() -> dict:
    try:
        with open(CFG_PATH) as f:
            return json.load(f)
    except Exception:
        return dict(DEFAULT_CFG)


def _save_cfg(cfg: dict):
    os.makedirs(os.path.dirname(CFG_PATH), exist_ok=True)
    with open(CFG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


def start():
    global _tunnel_proc
    if not _has_ssh():
        print(f"[{PLUGIN_NAME}] SSH not found. Install openssh:")
        print("  Linux : sudo apt install openssh-client")
        print("  Termux: pkg install openssh")
        return

    cfg = _load_cfg()
    if not cfg.get("remote_host"):
        print(f"[{PLUGIN_NAME}] No remote host configured. Run: sshbridge config")
        return

    with _lock:
        if _tunnel_proc and _tunnel_proc.poll() is None:
            print(f"[{PLUGIN_NAME}] Tunnel already running (PID {_tunnel_proc.pid}).")
            return

    cmd = [
        "ssh",
        "-N",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "ServerAliveInterval=30",
        "-L", f"{cfg['local_port']}:localhost:{cfg['remote_port']}",
    ]
    if cfg.get("identity"):
        cmd += ["-i", cfg["identity"]]
    cmd += cfg.get("extra_args", [])
    user = cfg.get("remote_user")
    host = cfg["remote_host"]
    cmd.append(f"{user}@{host}" if user else host)

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
        with _lock:
            _tunnel_proc = proc
        try:
            from kernel.kal import get_kal
            get_kal().register_process(PLUGIN_NAME, proc.pid,
                                       f"SSH tunnel to {host}:{cfg['remote_port']}")
        except Exception:
            pass
        try:
            from cc.events import get_event_bus, LEVEL_OK
            get_event_bus().emit(PLUGIN_NAME, LEVEL_OK,
                                 f"SSH tunnel started → {host}:{cfg['remote_port']} "
                                 f"(local :{cfg['local_port']})")
        except Exception:
            pass
        print(f"[{PLUGIN_NAME}] Tunnel started — "
              f"localhost:{cfg['local_port']} → {host}:{cfg['remote_port']} "
              f"(PID {proc.pid})")
    except Exception as e:
        print(f"[{PLUGIN_NAME}] Failed to start tunnel: {e}")


def stop():
    global _tunnel_proc
    with _lock:
        proc = _tunnel_proc
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        with _lock:
            _tunnel_proc = None
        try:
            from kernel.kal import get_kal
            get_kal().unregister_process(PLUGIN_NAME)
        except Exception:
            pass
        try:
            from cc.events import get_event_bus, LEVEL_INFO
            get_event_bus().emit(PLUGIN_NAME, LEVEL_INFO, "SSH tunnel stopped")
        except Exception:
            pass
        print(f"[{PLUGIN_NAME}] Tunnel stopped.")
    else:
        print(f"[{PLUGIN_NAME}] No active tunnel.")


def status():
    with _lock:
        proc = _tunnel_proc
    running = proc is not None and proc.poll() is None
    ssh_ok  = _has_ssh()
    cfg     = _load_cfg()

    print(f"[{PLUGIN_NAME}] v{PLUGIN_VERSION}")
    print(f"  SSH available : {'yes' if ssh_ok else 'NO — install openssh'}")
    print(f"  Tunnel active : {running}")
    if running:
        print(f"  PID           : {proc.pid}")
    print(f"  Remote host   : {cfg.get('remote_host') or '(not set)'}")
    print(f"  Remote user   : {cfg.get('remote_user') or '(not set)'}")
    print(f"  Remote port   : {cfg.get('remote_port', 22)}")
    print(f"  Local port    : {cfg.get('local_port', 2222)}")
    print(f"  Config file   : {CFG_PATH}")


def config(args=None):
    """Interactive config setter: sshbridge config <key> <value>"""
    args = args or []
    cfg  = _load_cfg()
    if len(args) < 2:
        print(f"  Usage: sshbridge config <key> <value>")
        print(f"  Keys: remote_host  remote_user  remote_port  local_port  identity")
        print(f"  Current config:")
        for k, v in cfg.items():
            if k != "extra_args":
                print(f"    {k:<16} = {v!r}")
        return
    key, val = args[0], args[1]
    if key in ("remote_port", "local_port"):
        try:
            val = int(val)
        except ValueError:
            print(f"  {key} must be an integer.")
            return
    cfg[key] = val
    _save_cfg(cfg)
    print(f"[{PLUGIN_NAME}] Config updated: {key} = {val!r}")


def help_cmd():
    print(f"""
  [{PLUGIN_NAME}] v{PLUGIN_VERSION} — SSH Tunnel Bridge
  Commands:
    start                    Start SSH tunnel using saved config
    stop                     Stop active tunnel
    status                   Show tunnel state + config
    config <key> <value>     Set a config value
    help                     This message
  Config keys:
    remote_host   Hostname or IP of remote server
    remote_user   SSH username
    remote_port   Remote port to forward (default 22)
    local_port    Local port to listen on (default 2222)
    identity      Path to SSH private key file
  Example:
    sshbridge config remote_host myserver.example.com
    sshbridge config remote_user pi
    sshbridge start
""")


def main(args=None):
    args = args or []
    cmd  = args[0] if args else "help"
    if   cmd == "start":   start()
    elif cmd == "stop":    stop()
    elif cmd == "status":  status()
    elif cmd == "config":  config(args[1:])
    elif cmd == "help":    help_cmd()
    else:
        print(f"[{PLUGIN_NAME}] Unknown command '{cmd}'. Try 'help'.")


if __name__ == "__main__":
    main(sys.argv[1:])
