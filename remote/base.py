"""
AIOS Remote Control Base
Provider-agnostic interface for connecting to and controlling remote systems.

Supports multiple remote host profiles. Each profile uses a registered
RemoteProvider backend so the actual transport (SSH, API, container, etc.)
can be swapped without changing the UI layer.
"""

import time
import threading
from typing import List, Dict, Optional


# ── Host profile model ────────────────────────────────────────────────────────

class RemoteHost:
    """Metadata for a remote host profile."""

    def __init__(self, name: str, host: str, port: int = 22,
                 auth: str = "", provider_name: str = ""):
        self.name          = name
        self.host          = host
        self.port          = port
        self.auth          = auth            # key path, token, etc.
        self.provider_name = provider_name
        self.status        = "disconnected"  # disconnected | connecting | connected | error
        self.last_sync     = None
        self.added_at      = time.strftime("%Y-%m-%dT%H:%M:%S")

    def summary(self) -> str:
        return f"{self.name} ({self.host}:{self.port}) [{self.status}]"


# ── RemoteManager ─────────────────────────────────────────────────────────────

class RemoteManager:
    """
    Central manager for remote host connections.

    Usage::

        from remote.base import get_remote_manager
        rm = get_remote_manager()
        rm.add_host("my-vps", "192.168.1.10", port=22)
        result = rm.run_command("my-vps", "uptime")
    """

    def __init__(self):
        self._lock      = threading.Lock()
        self._hosts: Dict[str, RemoteHost] = {}
        self._providers = {}   # provider name → RemoteProvider

    # ── Provider management ────────────────────────────────────────────

    def register_provider(self, provider) -> None:
        with self._lock:
            self._providers[provider.name] = provider

    def _get_provider(self, host: RemoteHost):
        """Return the provider for the given host, or None."""
        with self._lock:
            return self._providers.get(host.provider_name)

    # ── Host management ────────────────────────────────────────────────

    def add_host(self, name: str, host: str, port: int = 22,
                 auth: str = "", provider_name: str = "") -> RemoteHost:
        h = RemoteHost(name, host, port, auth, provider_name)
        with self._lock:
            self._hosts[name] = h
        try:
            from cc.events import get_event_bus, LEVEL_INFO
            get_event_bus().emit("remote", LEVEL_INFO,
                                 f"Host added: {name} ({host}:{port})")
        except Exception:
            pass
        return h

    def remove_host(self, name: str) -> bool:
        with self._lock:
            existed = name in self._hosts
            self._hosts.pop(name, None)
        return existed

    def get_host(self, name: str) -> Optional[RemoteHost]:
        with self._lock:
            return self._hosts.get(name)

    def list_hosts(self) -> List[RemoteHost]:
        with self._lock:
            return list(self._hosts.values())

    def host_count(self) -> int:
        with self._lock:
            return len(self._hosts)

    # ── Connection ─────────────────────────────────────────────────────

    def connect(self, name: str) -> dict:
        """Connect to a remote host. Returns {ok, message}."""
        host = self.get_host(name)
        if host is None:
            return {"ok": False, "message": f"Host not found: {name}"}
        provider = self._get_provider(host)
        if provider is None:
            return {"ok": False,
                    "message": f"No provider configured for host '{name}'. "
                               "Add a remote provider in Settings → Providers."}
        host.status = "connecting"
        ok = provider.connect()
        host.status = "connected" if ok else "error"
        if ok:
            try:
                from cc.events import get_event_bus, LEVEL_OK
                get_event_bus().emit("remote", LEVEL_OK,
                                     f"Connected: {name}")
            except Exception:
                pass
            return {"ok": True, "message": f"Connected to {name}."}
        return {"ok": False, "message": f"Connection failed to {name}."}

    def disconnect(self, name: str) -> dict:
        host = self.get_host(name)
        if host is None:
            return {"ok": False, "message": f"Host not found: {name}"}
        provider = self._get_provider(host)
        if provider:
            provider.disconnect()
        host.status = "disconnected"
        return {"ok": True, "message": f"Disconnected from {name}."}

    # ── Remote operations ──────────────────────────────────────────────

    def run_command(self, name: str, cmd: str) -> dict:
        """Run a command on the named host. Returns {ok, stdout, stderr}."""
        host = self.get_host(name)
        if host is None:
            return {"ok": False, "stdout": "", "stderr": f"Host not found: {name}"}
        if host.status != "connected":
            return {"ok": False, "stdout": "",
                    "stderr": f"Not connected to {name}. Use connect first."}
        provider = self._get_provider(host)
        if provider is None:
            return {"ok": False, "stdout": "",
                    "stderr": "No provider for this host."}
        result = provider.run_command(cmd)
        host.last_sync = time.strftime("%Y-%m-%dT%H:%M:%S")
        return result

    def deploy(self, name: str, local_path: str,
               remote_path: str) -> dict:
        """Push a file/directory to the remote host."""
        host = self.get_host(name)
        if host is None:
            return {"ok": False, "message": f"Host not found: {name}"}
        if host.status != "connected":
            return {"ok": False, "message": f"Not connected to {name}."}
        provider = self._get_provider(host)
        if provider is None:
            return {"ok": False, "message": "No provider for this host."}
        ok = provider.push_file(local_path, remote_path)
        if ok:
            host.last_sync = time.strftime("%Y-%m-%dT%H:%M:%S")
        return {"ok": ok, "message": "Deploy OK." if ok else "Deploy failed."}


# ── Singleton ──────────────────────────────────────────────────────────────────

_remote_manager_lock: __import__("threading").Lock = __import__("threading").Lock()
_remote_manager: RemoteManager = None


def get_remote_manager() -> RemoteManager:
    global _remote_manager
    if _remote_manager is None:
        with _remote_manager_lock:
            if _remote_manager is None:
                _remote_manager = RemoteManager()
    return _remote_manager
