"""
AIOS Boot Subsystem
POST-style boot screen with real system checks.
Format: [timestamp] [OK|FAIL|WARN] message
"""

import sys
import os
import time
import platform
import subprocess
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ── ANSI helpers ─────────────────────────────────────────────────────────────

RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RED    = "\033[1;31m"
GREEN  = "\033[1;32m"
YELLOW = "\033[1;33m"
BLUE   = "\033[1;34m"
CYAN   = "\033[1;36m"
WHITE  = "\033[1;37m"
GRAY   = "\033[0;37m"

TAG_OK   = f"{GREEN}[  OK  ]{RESET}"
TAG_FAIL = f"{RED}[ FAIL ]{RESET}"
TAG_WARN = f"{YELLOW}[ WARN ]{RESET}"
TAG_INFO = f"{BLUE}[ INFO ]{RESET}"
TAG_LOAD = f"{CYAN}[ LOAD ]{RESET}"


def _ts():
    return time.strftime("%H:%M:%S.") + f"{int(time.time() * 1000) % 1000:03d}"


def _line(tag, msg, delay=0.04):
    print(f"  {DIM}{_ts()}{RESET}  {tag}  {msg}")
    if delay:
        time.sleep(delay)


def _header():
    w = 72
    print()
    print(f"  {CYAN}{'═' * w}{RESET}")
    print(f"  {CYAN}║{RESET}  {BOLD}{WHITE}◈ AIOS  AUTONOMOUS INTELLIGENCE OPERATING SYSTEM{RESET}"
          f"{'':>16}{CYAN}║{RESET}")
    print(f"  {CYAN}║{RESET}  {GRAY}Boot Sequence v1.0.0  —  Kernel Abstraction Layer Active"
          f"{'':>8}{CYAN}║{RESET}")
    print(f"  {CYAN}{'═' * w}{RESET}")
    print()


def _section(title):
    print(f"\n  {BOLD}{BLUE}── {title} {'─' * (60 - len(title))}{RESET}")


# ── Individual checks ─────────────────────────────────────────────────────────

def _check_python():
    v = sys.version_info
    if v.major == 3 and v.minor >= 8:
        _line(TAG_OK, f"Python {v.major}.{v.minor}.{v.micro} — runtime verified")
        return True
    _line(TAG_FAIL, f"Python {v.major}.{v.minor} — requires Python 3.8+")
    return False


def _check_platform():
    p = platform.system()
    machine = platform.machine()
    _line(TAG_OK, f"Platform: {p} / {machine} — KAL interface ready")
    return True


def _check_memory():
    try:
        with open("/proc/meminfo") as f:
            lines = f.readlines()
        mem = {}
        for line in lines:
            parts = line.split()
            if parts[0].rstrip(":") in ("MemTotal", "MemAvailable"):
                mem[parts[0].rstrip(":")] = int(parts[1])
        total_mb = mem.get("MemTotal", 0) // 1024
        avail_mb = mem.get("MemAvailable", 0) // 1024
        if avail_mb < 50:
            _line(TAG_WARN, f"Memory low — {avail_mb}MB free / {total_mb}MB total")
            return True
        _line(TAG_OK, f"Memory: {avail_mb}MB free / {total_mb}MB total")
        return True
    except Exception:
        _line(TAG_WARN, "Memory info unavailable — /proc/meminfo not readable")
        return True


def _check_storage():
    try:
        stat = os.statvfs(ROOT)
        free_mb = (stat.f_bavail * stat.f_frsize) // (1024 * 1024)
        total_mb = (stat.f_blocks * stat.f_frsize) // (1024 * 1024)
        _line(TAG_OK, f"Storage: {free_mb}MB free / {total_mb}MB total at {ROOT}")
        return True
    except Exception:
        _line(TAG_WARN, "Storage check failed — continuing")
        return True


def _check_config():
    cfg_path = os.path.join(ROOT, "config", "aios.cfg")
    if os.path.isfile(cfg_path):
        try:
            with open(cfg_path) as f:
                json.load(f)
            _line(TAG_OK, f"Config loaded — {cfg_path}")
            return True
        except Exception as e:
            _line(TAG_FAIL, f"Config parse error: {e}")
            return False
    _line(TAG_WARN, "Config missing — using defaults")
    return True


def _check_kal():
    try:
        from kernel.kal import KAL
        k = KAL()
        _ = k.get_memory()
        _line(TAG_OK, "Kernel Abstraction Layer — initialized")
        return True
    except Exception as e:
        _line(TAG_FAIL, f"KAL init failed: {e}")
        return False


def _check_plugins():
    plug_dir = os.path.join(ROOT, "plugins", "installed")
    os.makedirs(plug_dir, exist_ok=True)
    plugins = [d for d in os.listdir(plug_dir)
               if os.path.isdir(os.path.join(plug_dir, d))]
    if plugins:
        _line(TAG_OK, f"Plugins: {len(plugins)} installed — {', '.join(plugins[:5])}")
    else:
        _line(TAG_INFO, "Plugins: none installed (use 'aios install <plugin>')")
    return True


def _check_tool(name, cmd):
    try:
        result = subprocess.run(
            cmd, capture_output=True, timeout=3
        )
        if result.returncode == 0:
            _line(TAG_OK, f"Tool: {name} — available")
            return True
        _line(TAG_WARN, f"Tool: {name} — not available (optional)")
        return True
    except FileNotFoundError:
        _line(TAG_WARN, f"Tool: {name} — not found (optional)")
        return True
    except Exception:
        _line(TAG_WARN, f"Tool: {name} — check failed (optional)")
        return True


def _check_aura():
    try:
        from ai.aura import Aura
        a = Aura()
        _line(TAG_OK, f"AURA AI Engine — mode: {a.mode}")
        return True
    except Exception as e:
        _line(TAG_WARN, f"AURA init deferred: {e}")
        return True


def _check_aim():
    try:
        from aim.aim import AIM
        _line(TAG_OK, "AIM — Adaptive Interface Mesh ready")
        return True
    except Exception as e:
        _line(TAG_WARN, f"AIM init deferred: {e}")
        return True


def _check_arrow():
    try:
        from shell.arrow import Arrow
        _line(TAG_OK, "ARROW Shell — Autonomous Routing Relay Orchestration Workflow ready")
        return True
    except Exception as e:
        _line(TAG_WARN, f"ARROW init deferred: {e}")
        return True


def _check_cc():
    try:
        import curses
        _line(TAG_OK, "Command Center — curses TUI engine available")
        return True
    except ImportError:
        _line(TAG_FAIL, "Command Center — curses not available")
        return False


def _check_data_dirs():
    dirs = [
        os.path.join(ROOT, "plugins", "installed"),
        os.path.join(ROOT, "config"),
        os.path.expanduser("~/.aios"),
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
    _line(TAG_OK, "Data directories — verified")
    return True


def _check_hub():
    try:
        from hub.device_profile import get_profile
        p = get_profile()
        _line(TAG_OK, f"Studio Hub — device mode: {p.mode} (refresh {p.refresh_sec}s)")
        return True
    except Exception as e:
        _line(TAG_WARN, f"Studio Hub init deferred: {e}")
        return True


def _check_autostart():
    """Load and start services listed in config.services.autostart."""
    try:
        from boot.service_loader import autostart_services
        started = autostart_services()
        if started:
            _line(TAG_OK, f"Autostart: {len(started)} service(s) started — {', '.join(started)}")
        else:
            _line(TAG_INFO, "Autostart: no services configured")
    except Exception as e:
        _line(TAG_WARN, f"Autostart: {e}")
    return True


# ── Bootloader class ──────────────────────────────────────────────────────────

class Bootloader:
    def __init__(self):
        self.failures = []
        self.warnings = []

    def _run_check(self, label, fn, critical=False):
        ok = fn()
        if not ok:
            if critical:
                self.failures.append(label)
            else:
                self.warnings.append(label)
        return ok

    def run(self) -> bool:
        _header()

        # ── Phase 1: Hardware / OS ────────────────────────────────────
        _section("PHASE 1 — HARDWARE & OS")
        self._run_check("python",   _check_python,   critical=True)
        self._run_check("platform", _check_platform, critical=False)
        self._run_check("memory",   _check_memory,   critical=False)
        self._run_check("storage",  _check_storage,  critical=False)

        # ── Phase 2: AIOS Core ────────────────────────────────────────
        _section("PHASE 2 — AIOS CORE")
        self._run_check("data_dirs", _check_data_dirs, critical=True)
        self._run_check("config",    _check_config,    critical=True)
        self._run_check("kal",       _check_kal,       critical=True)

        # ── Phase 3: Subsystems ───────────────────────────────────────
        _section("PHASE 3 — SUBSYSTEMS")
        self._run_check("hub",   _check_hub,   critical=False)
        self._run_check("aura",  _check_aura,  critical=False)
        self._run_check("aim",   _check_aim,   critical=False)
        self._run_check("arrow", _check_arrow, critical=False)
        self._run_check("cc",    _check_cc,    critical=True)

        # ── Phase 4: Plugins & Tools ──────────────────────────────────
        _section("PHASE 4 — PLUGINS & OPTIONAL TOOLS")
        self._run_check("plugins", _check_plugins, critical=False)
        _check_tool("git",    ["git",    "--version"])
        _check_tool("python3",["python3","--version"])
        _check_tool("curl",   ["curl",   "--version"])
        self._run_check("autostart", _check_autostart, critical=False)

        # ── Boot Summary ──────────────────────────────────────────────
        _section("BOOT SUMMARY")

        # Emit boot events to EventBus
        try:
            from cc.events import get_event_bus, LEVEL_OK, LEVEL_WARN, LEVEL_ERROR
            bus = get_event_bus()
            bus.emit("boot", LEVEL_OK, "AIOS boot sequence started")
            if self.failures:
                for f in self.failures:
                    bus.emit("boot", LEVEL_ERROR, f"Critical failure: {f}")
            if self.warnings:
                for w in self.warnings:
                    bus.emit("boot", LEVEL_WARN, f"Warning: {w}")
            if not self.failures:
                bus.emit("boot", LEVEL_OK, "Boot complete — all critical checks passed")
        except Exception:
            pass

        # Initialize hub state so last_panel persists across sessions
        try:
            from hub.hub_state import get_hub_state
            get_hub_state()   # triggers load from disk
        except Exception:
            pass

        if self.failures:
            for f in self.failures:
                _line(TAG_FAIL, f"Critical failure: {f}", delay=0)
            _line(TAG_FAIL, f"Boot FAILED — {len(self.failures)} critical error(s)", delay=0)
            print()
            return False

        if self.warnings:
            _line(TAG_WARN, f"{len(self.warnings)} warning(s) — non-critical, system continues")
        else:
            _line(TAG_OK, "All systems nominal")

        _line(TAG_OK, "Handing off to AIOS kernel...")
        time.sleep(0.3)
        _line(TAG_OK, "Launching Command Center...")
        time.sleep(0.3)
        print()
        return True
