"""
AIM — Adaptive Interface Mesh
Bridges AIOS to the existing web.
Acts as a local HTTP gateway: connects outbound when online,
queues requests when offline.
"""

import os
import json
import time
import threading
import socket
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import URLError
from urllib.parse import urlencode

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _check_internet(host: str = "8.8.8.8", port: int = 53, timeout: float = 3.0) -> bool:
    """Quick connectivity check via TCP socket."""
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except OSError:
        return False


class AIMRequest:
    def __init__(self, url: str, method: str = "GET",
                 data: Optional[dict] = None, headers: Optional[dict] = None):
        self.url     = url
        self.method  = method.upper()
        self.data    = data
        self.headers = headers or {}
        self.ts      = time.time()
        self.status  = "queued"
        self.result  = None
        self.error   = None


class AIM:
    """
    Adaptive Interface Mesh.

    Features:
      - Online/offline detection
      - HTTP GET/POST via Python urllib (no extra deps)
      - Request queue: replays queued requests when connection restores
      - Simple bridge API for AIOS subsystems
    """

    VERSION = "1.0.0"

    def __init__(self, cfg: dict = None):
        cfg = cfg or {}
        self.enabled        = cfg.get("enabled", True)
        self.proxy_enabled  = cfg.get("proxy_enabled", False)
        self._queue         = []
        self._online        = False
        self._lock          = threading.Lock()
        self._monitor_thread = None
        self._running       = False

    # ── Status ────────────────────────────────────────────────────────

    def is_online(self) -> bool:
        return self._online

    def get_status(self) -> dict:
        return {
            "version":       self.VERSION,
            "enabled":       self.enabled,
            "online":        self._online,
            "queued":        len(self._queue),
            "proxy_enabled": self.proxy_enabled,
        }

    # ── Start / Stop ──────────────────────────────────────────────────

    def start(self):
        """Start the AIM background connectivity monitor."""
        if self._running:
            return
        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True, name="aim-monitor"
        )
        self._monitor_thread.start()

    def stop(self):
        self._running = False

    def _monitor_loop(self):
        while self._running:
            was_online = self._online
            self._online = _check_internet()
            if not was_online and self._online:
                # Just came online: flush queue
                self._flush_queue()
            time.sleep(15)

    # ── HTTP ──────────────────────────────────────────────────────────

    def fetch(self, url: str, timeout: float = 10.0) -> dict:
        """
        Perform a GET request. If offline, queue the request.
        Returns: {ok, status_code, body, error}
        """
        if not self._online:
            req = AIMRequest(url)
            with self._lock:
                self._queue.append(req)
            return {"ok": False, "status_code": 0, "body": "",
                    "error": "offline — request queued"}

        return self._do_get(url, timeout)

    def post(self, url: str, data: dict, timeout: float = 10.0) -> dict:
        """POST JSON data to url."""
        if not self._online:
            req = AIMRequest(url, "POST", data)
            with self._lock:
                self._queue.append(req)
            return {"ok": False, "status_code": 0, "body": "",
                    "error": "offline — request queued"}

        return self._do_post(url, data, timeout)

    def _do_get(self, url: str, timeout: float = 10.0) -> dict:
        try:
            headers = {"User-Agent": "AIOS-AIM/1.0"}
            req = Request(url, headers=headers)
            with urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                return {"ok": True, "status_code": resp.status,
                        "body": body, "error": None}
        except URLError as e:
            return {"ok": False, "status_code": 0, "body": "", "error": str(e.reason)}
        except Exception as e:
            return {"ok": False, "status_code": 0, "body": "", "error": str(e)}

    def _do_post(self, url: str, data: dict, timeout: float = 10.0) -> dict:
        try:
            payload = json.dumps(data).encode("utf-8")
            headers = {
                "User-Agent":   "AIOS-AIM/1.0",
                "Content-Type": "application/json",
            }
            req = Request(url, data=payload, headers=headers, method="POST")
            with urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                return {"ok": True, "status_code": resp.status,
                        "body": body, "error": None}
        except Exception as e:
            return {"ok": False, "status_code": 0, "body": "", "error": str(e)}

    def _flush_queue(self):
        with self._lock:
            pending = list(self._queue)
            self._queue.clear()
        for req in pending:
            if req.method == "GET":
                self._do_get(req.url)
            elif req.method == "POST":
                self._do_post(req.url, req.data or {})

    def check_now(self) -> bool:
        """Force an immediate connectivity check."""
        self._online = _check_internet()
        return self._online


# Singleton
_aim_instance = None


def get_aim() -> AIM:
    global _aim_instance
    if _aim_instance is None:
        try:
            cfg_path = os.path.join(ROOT, "config", "aios.cfg")
            with open(cfg_path) as f:
                cfg = json.load(f)
            _aim_instance = AIM(cfg.get("aim", {}))
        except Exception:
            _aim_instance = AIM()
        _aim_instance.start()
    return _aim_instance
