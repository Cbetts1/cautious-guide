"""
AIOS Plugin: monitor
System resource monitor service.
Samples CPU, memory, and disk every 5 seconds; appends to ~/.aios/monitor.log.
Log is rotated when it exceeds LOG_MAX_BYTES (default 10 MB).
Registers itself with the KAL ProcessRegistry.
"""

import os
import sys
import time
import threading
import json

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

PLUGIN_NAME    = "monitor"
PLUGIN_VERSION = "1.0.0"
LOG_PATH       = os.path.expanduser("~/.aios/monitor.log")
LOG_MAX_BYTES  = 10 * 1024 * 1024   # 10 MB — rotate when exceeded
INTERVAL       = 5   # seconds between samples

_running   = False
_thread    = None
_lock      = threading.Lock()
_log_fh    = None


def _rotate_if_needed():
    """Rotate monitor.log → monitor.log.1 when it exceeds LOG_MAX_BYTES."""
    global _log_fh
    try:
        if _log_fh is None:
            return
        size = os.fstat(_log_fh.fileno()).st_size
        if size < LOG_MAX_BYTES:
            return
        _log_fh.close()
        _log_fh = None
        rotated = LOG_PATH + ".1"
        if os.path.isfile(rotated):
            os.remove(rotated)
        os.rename(LOG_PATH, rotated)
        _log_fh = open(LOG_PATH, "a", buffering=1)
    except Exception:
        pass


def _sample() -> dict:
    """Collect a single resource snapshot."""
    sample = {"ts": time.strftime("%Y-%m-%d %H:%M:%S")}
    try:
        from kernel.kal import get_kal
        kal = get_kal()
        mem  = kal.get_memory()
        cpu  = kal.get_cpu_percent()
        disk = kal.get_disk_usage(ROOT)
        sample.update({
            "cpu_pct":    cpu,
            "mem_used_mb":  mem["used_mb"],
            "mem_total_mb": mem["total_mb"],
            "mem_pct":    mem["percent"],
            "disk_used_mb":  disk["used_mb"],
            "disk_total_mb": disk["total_mb"],
            "disk_pct":   disk["percent"],
        })
    except Exception as e:
        sample["error"] = str(e)
    return sample


def _monitor_loop():
    global _running, _log_fh
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    try:
        _log_fh = open(LOG_PATH, "a", buffering=1)
    except Exception:
        _log_fh = None

    try:
        from cc.events import get_event_bus, LEVEL_INFO
        get_event_bus().emit(PLUGIN_NAME, LEVEL_INFO, "Monitor service started")
    except Exception:
        pass

    while _running:
        s = _sample()
        line = json.dumps(s)
        if _log_fh:
            try:
                _log_fh.write(line + "\n")
                _rotate_if_needed()
            except Exception:
                pass
        time.sleep(INTERVAL)

    if _log_fh:
        try:
            _log_fh.close()
        except Exception:
            pass

    try:
        from cc.events import get_event_bus, LEVEL_INFO
        get_event_bus().emit(PLUGIN_NAME, LEVEL_INFO, "Monitor service stopped")
    except Exception:
        pass


def start():
    global _running, _thread
    with _lock:
        if _running:
            return
        _running = True
        _thread = threading.Thread(
            target=_monitor_loop, daemon=True, name="svc-monitor"
        )
        _thread.start()
    try:
        from kernel.kal import get_kal
        import os as _os
        get_kal().register_process(PLUGIN_NAME, _os.getpid(), "system resource monitor")
    except Exception:
        pass
    print(f"[{PLUGIN_NAME}] Monitor started. Log: {LOG_PATH}")


def stop():
    global _running
    with _lock:
        _running = False
    try:
        from kernel.kal import get_kal
        get_kal().unregister_process(PLUGIN_NAME)
    except Exception:
        pass
    print(f"[{PLUGIN_NAME}] Monitor stopped.")


def status():
    with _lock:
        running = _running
    s = _sample()
    print(f"[{PLUGIN_NAME}] v{PLUGIN_VERSION}")
    print(f"  Running : {running}")
    print(f"  Log     : {LOG_PATH}")
    print(f"  CPU     : {s.get('cpu_pct', '?')}%")
    print(f"  Memory  : {s.get('mem_used_mb', '?')}/{s.get('mem_total_mb', '?')} MB "
          f"({s.get('mem_pct', '?')}%)")
    print(f"  Disk    : {s.get('disk_used_mb', '?')}/{s.get('disk_total_mb', '?')} MB "
          f"({s.get('disk_pct', '?')}%)")


def tail(n: int = 10):
    """Print last n log entries."""
    try:
        with open(LOG_PATH) as f:
            lines = f.readlines()
        for line in lines[-n:]:
            try:
                d = json.loads(line)
                print(f"  {d.get('ts','?')}  CPU:{d.get('cpu_pct','?')}%  "
                      f"MEM:{d.get('mem_pct','?')}%  DISK:{d.get('disk_pct','?')}%")
            except Exception:
                print(f"  {line.rstrip()}")
    except FileNotFoundError:
        print(f"[{PLUGIN_NAME}] No log yet — start the monitor first.")


def help_cmd():
    print(f"""
  [{PLUGIN_NAME}] v{PLUGIN_VERSION} — System Resource Monitor
  Commands:
    start   Start the monitor background service
    stop    Stop the monitor service
    status  Show current resource snapshot + service state
    tail    Print last 10 log entries
    help    This message
  Log file: {LOG_PATH}
""")


def main(args=None):
    args = args or []
    cmd  = args[0] if args else "help"
    if   cmd == "start":  start()
    elif cmd == "stop":   stop()
    elif cmd == "status": status()
    elif cmd == "tail":
        n = int(args[1]) if len(args) > 1 else 10
        tail(n)
    elif cmd == "help":   help_cmd()
    else:
        print(f"[{PLUGIN_NAME}] Unknown command '{cmd}'. Try 'help'.")


if __name__ == "__main__":
    main(sys.argv[1:])
