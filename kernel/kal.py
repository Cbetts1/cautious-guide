"""
AIOS Kernel Abstraction Layer (KAL)
All AIOS subsystems call KAL for system resources.
Swap the KAL implementation to run on a custom kernel later
without changing any higher-level code.
"""

import os
import sys
import subprocess
import platform
import time

from kernel.memory import read_meminfo, read_cpu_percent
from kernel.process import ProcessRegistry


class KAL:
    """
    Kernel Abstraction Layer.

    Provides a stable interface for:
      - Memory / CPU stats
      - Process management
      - Command execution
      - File system access
      - System metadata
    """

    VERSION = "1.0.0"
    KERNEL_NAME = "Linux"          # swap here when moving to custom kernel

    def __init__(self):
        self.proc_registry = ProcessRegistry()
        self._boot_time = time.time()

    # ── Metadata ──────────────────────────────────────────────────────

    def get_version(self) -> str:
        return self.VERSION

    def get_kernel_name(self) -> str:
        return self.KERNEL_NAME

    def get_hostname(self) -> str:
        try:
            return platform.node() or "aios-node"
        except Exception:
            return "aios-node"

    def get_platform_info(self) -> dict:
        return {
            "system":   platform.system(),
            "release":  platform.release(),
            "machine":  platform.machine(),
            "python":   platform.python_version(),
            "hostname": self.get_hostname(),
        }

    def get_uptime_seconds(self) -> float:
        return time.time() - self._boot_time

    def get_uptime_str(self) -> str:
        sec = int(self.get_uptime_seconds())
        d, sec = divmod(sec, 86400)
        h, sec = divmod(sec, 3600)
        m, s   = divmod(sec, 60)
        return f"{d}d {h}h {m}m {s}s"

    # ── Memory ────────────────────────────────────────────────────────

    def get_memory(self) -> dict:
        """
        Returns dict with keys: total_mb, available_mb, used_mb, percent
        """
        return read_meminfo()

    # ── CPU ───────────────────────────────────────────────────────────

    def get_cpu_percent(self) -> float:
        """Returns estimated CPU usage as a float 0–100."""
        return read_cpu_percent()

    # ── Processes ─────────────────────────────────────────────────────

    def register_process(self, name: str, pid: int, description: str = ""):
        self.proc_registry.register(name, pid, description)

    def unregister_process(self, name: str):
        self.proc_registry.unregister(name)

    def list_processes(self) -> list:
        return self.proc_registry.list()

    # ── Command execution ─────────────────────────────────────────────

    def run_command(self, cmd: list, capture: bool = True,
                    timeout: int = 30, cwd: str = None) -> dict:
        """
        Execute a system command through the KAL.
        Returns dict: {returncode, stdout, stderr}
        """
        try:
            result = subprocess.run(
                cmd,
                capture_output=capture,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )
            return {
                "returncode": result.returncode,
                "stdout": result.stdout if capture else "",
                "stderr": result.stderr if capture else "",
            }
        except FileNotFoundError:
            return {"returncode": 127, "stdout": "", "stderr": f"command not found: {cmd[0]}"}
        except subprocess.TimeoutExpired:
            return {"returncode": 124, "stdout": "", "stderr": "command timed out"}
        except Exception as e:
            return {"returncode": 1, "stdout": "", "stderr": str(e)}

    def run_shell(self, cmd_str: str, timeout: int = 30, cwd: str = None) -> dict:
        """Run a shell string command (bash -c)."""
        return self.run_command(
            ["bash", "-c", cmd_str],
            capture=True, timeout=timeout, cwd=cwd
        )

    # ── File system ───────────────────────────────────────────────────

    def get_disk_usage(self, path: str = "/") -> dict:
        """Returns dict: total_mb, used_mb, free_mb, percent"""
        try:
            stat = os.statvfs(path)
            total = (stat.f_blocks * stat.f_frsize) // (1024 * 1024)
            free  = (stat.f_bavail * stat.f_frsize) // (1024 * 1024)
            used  = total - free
            pct   = round((used / total * 100) if total else 0, 1)
            return {"total_mb": total, "used_mb": used, "free_mb": free, "percent": pct}
        except Exception:
            return {"total_mb": 0, "used_mb": 0, "free_mb": 0, "percent": 0}

    # ── Network ───────────────────────────────────────────────────────

    def get_network_info(self) -> dict:
        """Returns basic network interface info."""
        info = {"interfaces": [], "connected": False}
        try:
            result = self.run_command(["ip", "addr", "show"])
            if result["returncode"] == 0:
                lines = result["stdout"].splitlines()
                current = None
                for line in lines:
                    line = line.strip()
                    if line and line[0].isdigit():
                        parts = line.split(":")
                        if len(parts) >= 2:
                            current = parts[1].strip()
                    elif line.startswith("inet ") and current:
                        ip = line.split()[1]
                        info["interfaces"].append({"name": current, "ip": ip})
                        if not current.startswith("lo"):
                            info["connected"] = True
        except Exception:
            pass
        return info


# Singleton
_kal_instance = None


def get_kal() -> KAL:
    global _kal_instance
    if _kal_instance is None:
        _kal_instance = KAL()
    return _kal_instance
