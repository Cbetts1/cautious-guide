"""
AIOS Memory Monitor
Reads real memory and CPU stats from /proc on Linux/Termux.
Falls back to subprocess-based reads on other platforms.
"""

import time


def read_meminfo() -> dict:
    """
    Read memory from /proc/meminfo.
    Returns: {total_mb, available_mb, used_mb, percent}
    """
    result = {"total_mb": 0, "available_mb": 0, "used_mb": 0, "percent": 0.0}
    try:
        with open("/proc/meminfo") as f:
            raw = f.read()
        fields = {}
        for line in raw.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                key = parts[0].rstrip(":")
                val = int(parts[1])
                fields[key] = val

        total = fields.get("MemTotal", 0)
        avail = fields.get("MemAvailable", 0)
        used  = total - avail
        pct   = round((used / total * 100) if total else 0.0, 1)

        result = {
            "total_mb":     total // 1024,
            "available_mb": avail // 1024,
            "used_mb":      used  // 1024,
            "percent":      pct,
        }
    except Exception:
        # Fallback: try free command
        try:
            import subprocess
            r = subprocess.run(["free", "-m"], capture_output=True, text=True, timeout=3)
            for line in r.stdout.splitlines():
                if line.startswith("Mem:"):
                    parts = line.split()
                    total = int(parts[1])
                    used  = int(parts[2])
                    avail = int(parts[6]) if len(parts) > 6 else (total - used)
                    pct   = round((used / total * 100) if total else 0.0, 1)
                    result = {
                        "total_mb":     total,
                        "available_mb": avail,
                        "used_mb":      used,
                        "percent":      pct,
                    }
                    break
        except Exception:
            pass
    return result


# ── CPU measurement ───────────────────────────────────────────────────────────

_cpu_last = None  # (idle, total) at last sample time


def read_cpu_percent(interval: float = 0.1) -> float:
    """
    Measure CPU usage by sampling /proc/stat twice.
    Returns float 0–100.
    """
    global _cpu_last
    try:
        def _read_stat():
            with open("/proc/stat") as f:
                line = f.readline()
            parts = line.split()[1:]
            nums = [int(x) for x in parts[:8]]
            # user nice system idle iowait irq softirq steal
            idle  = nums[3] + nums[4]  # idle + iowait
            total = sum(nums)
            return idle, total

        t1 = _read_stat()

        if _cpu_last is None:
            time.sleep(interval)
            t2 = _read_stat()
        else:
            t2 = _read_stat()

        _cpu_last = t2

        idle_delta  = t2[0] - t1[0]
        total_delta = t2[1] - t1[1]

        if total_delta == 0:
            return 0.0
        cpu_used = total_delta - idle_delta
        return round((cpu_used / total_delta) * 100, 1)

    except Exception:
        return 0.0
