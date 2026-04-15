"""
AIOS Device Profile
Detects device capability and selects an appropriate performance mode.

Modes:
  lite      — minimal polling, reduced redraws; safe for low-spec phones
  balanced  — moderate polling; suitable for mid-range devices (default)
  full      — full features, faster refresh; for desktops/high-spec devices

The profile is chosen automatically at startup but can be overridden via
config (hub.device_mode) or at runtime.
"""

import os

# ── Mode constants ─────────────────────────────────────────────────────────────
MODE_LITE     = "lite"
MODE_BALANCED = "balanced"
MODE_FULL     = "full"

# Stats refresh interval (seconds) per mode
REFRESH_INTERVALS = {
    MODE_LITE:     5,
    MODE_BALANCED: 2,
    MODE_FULL:     1,
}

# Curses getch() timeout (ms) per mode — lower = more responsive but burns CPU
GETCH_TIMEOUTS = {
    MODE_LITE:     1000,
    MODE_BALANCED: 500,
    MODE_FULL:     250,
}


def _read_meminfo_mb() -> int:
    """Return total RAM in MB, or 0 on failure."""
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) // 1024
    except Exception:
        pass
    return 0


def _cpu_count() -> int:
    """Return number of online CPUs, or 1 on failure."""
    try:
        count = 0
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("processor"):
                    count += 1
        return max(1, count)
    except Exception:
        pass
    return 1


def detect_mode() -> str:
    """
    Auto-detect a sensible performance mode based on available RAM and CPU cores.

    Rules (conservative, phone-friendly):
      < 512 MB RAM or 1 CPU  → lite
      < 2 GB  RAM or ≤ 2 CPU → balanced
      else                   → full
    """
    ram_mb  = _read_meminfo_mb()
    cpus    = _cpu_count()

    if ram_mb > 0 and (ram_mb < 512 or cpus <= 1):
        return MODE_LITE
    if ram_mb > 0 and (ram_mb < 2048 or cpus <= 2):
        return MODE_BALANCED
    return MODE_FULL


# ── DeviceProfile singleton ────────────────────────────────────────────────────

class DeviceProfile:
    """
    Holds the active performance mode and exposes per-mode parameters.

    Usage::

        from hub.device_profile import get_profile
        p = get_profile()
        p.mode          # 'lite' | 'balanced' | 'full'
        p.refresh_sec   # stats poll interval
        p.getch_ms      # curses timeout
    """

    def __init__(self, mode: str = None):
        if mode is None:
            mode = self._load_config_mode()
        if mode not in (MODE_LITE, MODE_BALANCED, MODE_FULL):
            mode = detect_mode()
        self._mode = mode

    def _load_config_mode(self) -> str:
        """Try to read hub.device_mode from aios.cfg; fall back to auto-detect."""
        try:
            import json
            root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cfg_path = os.path.join(root, "config", "aios.cfg")
            with open(cfg_path) as f:
                cfg = json.load(f)
            mode = cfg.get("hub", {}).get("device_mode", "")
            if mode in (MODE_LITE, MODE_BALANCED, MODE_FULL):
                return mode
        except Exception:
            pass
        return detect_mode()

    @property
    def mode(self) -> str:
        return self._mode

    @mode.setter
    def mode(self, value: str):
        if value in (MODE_LITE, MODE_BALANCED, MODE_FULL):
            self._mode = value

    @property
    def refresh_sec(self) -> int:
        return REFRESH_INTERVALS.get(self._mode, 2)

    @property
    def getch_ms(self) -> int:
        return GETCH_TIMEOUTS.get(self._mode, 500)

    @property
    def is_lite(self) -> bool:
        return self._mode == MODE_LITE

    def summary(self) -> str:
        ram_mb = _read_meminfo_mb()
        cpus   = _cpu_count()
        return (
            f"mode={self._mode}  RAM={ram_mb}MB  CPUs={cpus}  "
            f"refresh={self.refresh_sec}s  getch={self.getch_ms}ms"
        )


import threading as _threading

_profile_lock: _threading.Lock = _threading.Lock()
_profile: DeviceProfile = None


def get_profile() -> DeviceProfile:
    global _profile
    if _profile is None:
        with _profile_lock:
            if _profile is None:
                _profile = DeviceProfile()
    return _profile
