"""
AIOS Plugin: webserver
Lightweight HTTP file server using Python's built-in http.server.
Serves the AIOS root directory.

By default the server binds to 127.0.0.1 (loopback only).
Pass bind="0.0.0.0" to start() if you intentionally want network-wide access.
Starts/stops cleanly; registers with KAL.
"""

import os
import sys
import threading
import socketserver
import http.server

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

PLUGIN_NAME    = "webserver"
PLUGIN_VERSION = "1.0.0"
DEFAULT_PORT   = 8080
DEFAULT_HOST   = "127.0.0.1"   # localhost-only by default; use "" for all interfaces

_server    = None
_thread    = None
_lock      = threading.Lock()
_port      = DEFAULT_PORT
_bind_addr = DEFAULT_HOST


class _SilentHandler(http.server.SimpleHTTPRequestHandler):
    """SimpleHTTPRequestHandler that suppresses request logs."""

    def log_message(self, fmt, *args):  # noqa: ARG002
        try:
            from cc.events import get_event_bus, LEVEL_INFO
            get_event_bus().emit(PLUGIN_NAME, LEVEL_INFO,
                                 f"{self.address_string()} - {args[0]}")
        except Exception:
            pass

    def log_error(self, fmt, *args):
        try:
            from cc.events import get_event_bus, LEVEL_ERROR
            get_event_bus().emit(PLUGIN_NAME, LEVEL_ERROR,
                                 f"HTTP error: {args[0] if args else fmt}")
        except Exception:
            pass


def start(port: int = None, host: str = None):
    global _server, _thread, _port
    with _lock:
        if _server is not None:
            print(f"[{PLUGIN_NAME}] Already running on {_bind_addr}:{_port}.")
            return
        _port = port or DEFAULT_PORT
        _host = host if host is not None else DEFAULT_HOST
        try:
            handler = lambda *a, **kw: _SilentHandler(  # noqa: E731
                *a, directory=ROOT, **kw)
            _server = socketserver.TCPServer((_host, _port), handler)
            _server.allow_reuse_address = True
        except OSError as e:
            print(f"[{PLUGIN_NAME}] Could not bind to {_host}:{_port}: {e}")
            _server = None
            return

    def _serve():
        try:
            _server.serve_forever()
        except Exception:
            pass

    _thread = threading.Thread(target=_serve, daemon=True, name="svc-webserver")
    _thread.start()

    # Register with KAL using pid=0 — the server runs in a daemon thread,
    # not a separate process, so there is no distinct PID to report.
    try:
        from kernel.kal import get_kal
        get_kal().register_process(PLUGIN_NAME, os.getpid(),
                                   f"HTTP file server on {_host}:{_port}")
    except Exception:
        pass
    try:
        from cc.events import get_event_bus, LEVEL_OK
        get_event_bus().emit(PLUGIN_NAME, LEVEL_OK,
                             f"HTTP server started on http://{_host}:{_port}/")
    except Exception:
        pass
    print(f"[{PLUGIN_NAME}] Serving {ROOT} on http://{_host}:{_port}/")


def stop():
    global _server, _thread
    with _lock:
        if _server is None:
            print(f"[{PLUGIN_NAME}] Not running.")
            return
        try:
            _server.shutdown()
            _server.server_close()
        except Exception:
            pass
        _server = None
        _thread = None
    try:
        from kernel.kal import get_kal
        get_kal().unregister_process(PLUGIN_NAME)
    except Exception:
        pass
    try:
        from cc.events import get_event_bus, LEVEL_INFO
        get_event_bus().emit(PLUGIN_NAME, LEVEL_INFO, "HTTP server stopped")
    except Exception:
        pass
    print(f"[{PLUGIN_NAME}] Stopped.")


def status():
    with _lock:
        running = _server is not None
    if running:
        print(f"[{PLUGIN_NAME}] v{PLUGIN_VERSION} — RUNNING on http://{DEFAULT_HOST}:{_port}/")
        print(f"  Serving: {ROOT}")
    else:
        print(f"[{PLUGIN_NAME}] v{PLUGIN_VERSION} — STOPPED")
    print(f"  Default bind : {DEFAULT_HOST}:{DEFAULT_PORT}")


def help_cmd():
    print(f"""
  [{PLUGIN_NAME}] v{PLUGIN_VERSION} — HTTP File Server
  Commands:
    start [port]   Start server (default port {DEFAULT_PORT}, bind {DEFAULT_HOST})
    stop           Stop server
    status         Show server state
    help           This message
  Access: http://{DEFAULT_HOST}:{DEFAULT_PORT}/
  Note:   The server binds to {DEFAULT_HOST} (localhost only) by default.
""")


def main(args=None):
    args = args or []
    cmd  = args[0] if args else "help"
    if cmd == "start":
        port = int(args[1]) if len(args) > 1 else DEFAULT_PORT
        bind = args[2] if len(args) > 2 else DEFAULT_HOST
        start(port, bind)
    elif cmd == "stop":   stop()
    elif cmd == "status": status()
    elif cmd == "help":   help_cmd()
    else:
        print(f"[{PLUGIN_NAME}] Unknown command '{cmd}'. Try 'help'.")


if __name__ == "__main__":
    main(sys.argv[1:])
