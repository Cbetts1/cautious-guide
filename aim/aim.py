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
import ipaddress as _ipaddress
import sys
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import URLError
from urllib.parse import urlencode

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from version import __version__ as _VERSION  # noqa: E402

# ── Private address ranges blocked for SSRF protection ───────────────────────
_BLOCKED_HOSTS = {"localhost", "local"}


def _validate_external_url(url: str) -> str:
    """
    Return an error string if the URL should be blocked, or '' if it is safe.
    Allows only http:// and https:// to non-private/loopback destinations.
    Uses the ipaddress module to catch octal, decimal, hex, and IPv6 forms.
    """
    from urllib.parse import urlparse as _urlparse
    try:
        parsed = _urlparse(url)
    except Exception:
        return "invalid URL"
    if parsed.scheme not in ("http", "https"):
        return f"unsupported scheme '{parsed.scheme}' — only http/https allowed"
    host = (parsed.hostname or "").lower()
    if not host:
        return "missing host"

    # If the host looks like an IP address (including decimal/hex encodings),
    # parse it with ipaddress for the most reliable private-range check.
    try:
        ip = _ipaddress.ip_address(host)
        # For IPv4-mapped IPv6 (::ffff:127.0.0.1) also check the embedded address.
        if isinstance(ip, _ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
            embedded = ip.ipv4_mapped
            if (embedded.is_private or embedded.is_loopback
                    or embedded.is_link_local or embedded.is_reserved):
                return f"host '{host}' contains a private IPv4-mapped address"
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            return f"host '{host}' is a non-routable IP address"
        return ""  # Valid public IP — no further checks needed
    except ValueError:
        pass  # Not a dotted-notation IP literal; fall through

    # Handle decimal integer IP notation (e.g. 2130706433 == 127.0.0.1).
    # Python's ipaddress.ip_address() accepts ints but not integer strings.
    if host.isdigit():
        try:
            ip = _ipaddress.ip_address(int(host))
            if (ip.is_private or ip.is_loopback or ip.is_link_local
                    or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
                return f"host '{host}' is a non-routable IP address"
            return ""
        except ValueError:
            pass

    # Block known private hostnames
    if host in _BLOCKED_HOSTS:
        return f"host '{host}' is not allowed"

    # Block common private hostname prefixes
    _BLOCKED_PREFIXES = (
        "127.", "10.", "0.", "169.254.", "192.168.",
        "::1", "fc", "fd",
    )
    for prefix in _BLOCKED_PREFIXES:
        if host.startswith(prefix):
            return f"host '{host}' resolves to a private/loopback address"

    # Block 172.16.0.0/12 (Docker/private)
    if host.startswith("172."):
        try:
            second = int(host.split(".")[1])
            if 16 <= second <= 31:
                return f"host '{host}' is in a private address range"
        except (IndexError, ValueError):
            pass

    return ""


def _check_internet(host: str = "8.8.8.8", port: int = 53, timeout: float = 3.0) -> bool:
    """Quick connectivity check via TCP socket (no global timeout side-effects)."""
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
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

    VERSION = _VERSION

    def __init__(self, cfg: dict = None):
        cfg = cfg or {}
        self.enabled          = cfg.get("enabled", True)
        self.proxy_enabled    = cfg.get("proxy_enabled", False)
        self._bridge_port     = cfg.get("bridge_port", 7070)
        self._queue           = []
        self._online          = False
        self._lock            = threading.Lock()
        self._monitor_thread  = None
        self._running         = False
        self._gateway_server  = None
        self._gateway_thread  = None

    # ── Status ────────────────────────────────────────────────────────

    def is_online(self) -> bool:
        return self._online

    def get_status(self) -> dict:
        status = {
            "version":       self.VERSION,
            "enabled":       self.enabled,
            "online":        self._online,
            "queued":        len(self._queue),
            "proxy_enabled": self.proxy_enabled,
        }
        if self._gateway_server is not None:
            status["gateway_port"] = self._bridge_port
        return status

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
        try:
            from cc.events import get_event_bus, LEVEL_OK
            get_event_bus().emit("AIM", LEVEL_OK, "AIM connectivity monitor started")
        except Exception:
            pass

    def stop(self):
        self._running = False
        self.stop_gateway()

    def _monitor_loop(self):
        while self._running:
            was_online = self._online
            self._online = _check_internet()
            if not was_online and self._online:
                # Just came online: flush queue
                self._flush_queue()
                try:
                    from cc.events import get_event_bus, LEVEL_OK
                    get_event_bus().emit("AIM", LEVEL_OK, "Network connectivity restored — queue flushed")
                except Exception:
                    pass
            elif was_online and not self._online:
                try:
                    from cc.events import get_event_bus, LEVEL_WARN
                    get_event_bus().emit("AIM", LEVEL_WARN, "Network connectivity lost — requests will queue")
                except Exception:
                    pass
            time.sleep(15)

    # ── Local HTTP Gateway ────────────────────────────────────────────

    def start_gateway(self, port: int = None):
        """
        Start a local HTTP gateway server.
        Endpoints:
          GET /status        — return AIM JSON status
          GET /fetch?url=... — proxy a URL fetch
        Returns (ok, message).
        """
        import http.server
        import socketserver
        from urllib.parse import urlparse, parse_qs

        if self._gateway_server is not None:
            return False, f"Gateway already running on :{self._bridge_port}"

        port = port or self._bridge_port
        aim_ref = self

        class _GatewayHandler(http.server.BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):  # noqa: ARG002
                pass  # suppress default logging

            def do_GET(self):
                parsed = urlparse(self.path)
                path   = parsed.path.rstrip("/")

                if path == "/status":
                    body = json.dumps(aim_ref.get_status()).encode()
                    self._respond(200, "application/json", body)

                elif path == "/fetch":
                    qs  = parse_qs(parsed.query)
                    url = qs.get("url", [None])[0]
                    if not url:
                        body = b'{"error": "missing url parameter"}'
                        self._respond(400, "application/json", body)
                        return
                    # Validate URL to prevent SSRF: allow only http(s) to non-private hosts
                    err_msg = _validate_external_url(url)
                    if err_msg:
                        body = json.dumps({"error": err_msg}).encode()
                        self._respond(400, "application/json", body)
                        return
                    result = aim_ref._do_get(url)
                    if result["ok"]:
                        body = result["body"].encode("utf-8", errors="replace")
                        self._respond(200, "text/plain; charset=utf-8", body)
                    else:
                        err  = json.dumps({"error": result["error"]}).encode()
                        self._respond(502, "application/json", err)

                else:
                    body = b'{"error": "not found"}'
                    self._respond(404, "application/json", body)

            def _respond(self, code, ctype, body: bytes):
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        # allow_reuse_address must be set as a class attribute *before* TCPServer
        # calls server_bind() in __init__, otherwise the flag has no effect.
        class _ReusableGatewayServer(socketserver.TCPServer):
            allow_reuse_address = True

        try:
            srv = _ReusableGatewayServer(("127.0.0.1", port), _GatewayHandler)
        except OSError as e:
            return False, f"Could not bind gateway to :{port}: {e}"

        self._gateway_server = srv
        self._bridge_port    = port

        def _serve():
            try:
                srv.serve_forever()
            except Exception:
                pass

        self._gateway_thread = threading.Thread(
            target=_serve, daemon=True, name="aim-gateway"
        )
        self._gateway_thread.start()

        try:
            from cc.events import get_event_bus, LEVEL_OK
            get_event_bus().emit("AIM", LEVEL_OK,
                                 f"Local HTTP gateway started on http://127.0.0.1:{port}/")
        except Exception:
            pass

        return True, f"AIM gateway running on http://127.0.0.1:{port}/"

    def stop_gateway(self):
        """Stop the local HTTP gateway."""
        if self._gateway_server is None:
            return
        try:
            self._gateway_server.shutdown()
            self._gateway_server.server_close()
        except Exception:
            pass
        self._gateway_server = None
        self._gateway_thread = None
        try:
            from cc.events import get_event_bus, LEVEL_INFO
            get_event_bus().emit("AIM", LEVEL_INFO, "Local HTTP gateway stopped")
        except Exception:
            pass

    # ── HTTP ──────────────────────────────────────────────────────────

    def fetch(self, url: str, timeout: float = 10.0) -> dict:
        """
        Perform a GET request. If offline, queue the request.
        Returns: {ok, status_code, body, error}
        """
        err = _validate_external_url(url)
        if err:
            return {"ok": False, "status_code": 0, "body": "", "error": err}
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
_aim_lock = threading.Lock()


def get_aim() -> AIM:
    global _aim_instance
    with _aim_lock:
        if _aim_instance is None:
            try:
                cfg_path = os.path.join(ROOT, "config", "aios.cfg")
                with open(cfg_path) as f:
                    cfg = json.load(f)
                _aim_instance = AIM(cfg.get("aim", {}))
            except Exception as e:
                import sys as _sys
                print(f"[AIM] Warning: could not load config ({e}), using defaults",
                      file=_sys.stderr)
                _aim_instance = AIM()
            _aim_instance.start()
    return _aim_instance
