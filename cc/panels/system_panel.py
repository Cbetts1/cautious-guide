"""CC Panel: System — real-time system info."""
import os
import time
import platform

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class SystemPanel:
    TITLE = "SYSTEM"

    def render(self, win, y: int, x: int, height: int, width: int,
               kal=None, curses_mod=None):
        c = curses_mod
        if kal is None:
            return
        try:
            info = kal.get_platform_info()
            mem  = kal.get_memory()
            cpu  = kal.get_cpu_percent()
            disk = kal.get_disk_usage(ROOT)
            up   = kal.get_uptime_str()

            row = y

            def addline(text, attr=0):
                nonlocal row
                if row < y + height - 1:
                    try:
                        win.addnstr(row, x, text, width - 1, attr)
                    except Exception:
                        pass
                    row += 1

            # Section: Identity
            addline("  IDENTITY", c.color_pair(3) | c.A_BOLD)
            addline(f"  Hostname  : {info['hostname']}")
            addline(f"  Platform  : {info['system']} {info['release']}")
            addline(f"  Arch      : {info['machine']}")
            addline(f"  Python    : {info['python']}")
            addline(f"  KAL       : Linux Abstraction Layer v1.0.0")
            addline(f"  AIOS      : 1.0.0")
            addline(f"  Uptime    : {up}")
            addline("")

            # Section: Resources
            addline("  RESOURCES", c.color_pair(3) | c.A_BOLD)
            mem_pct = mem["percent"]
            bar_w   = max(10, width - 28)
            filled  = int(bar_w * mem_pct / 100)
            bar     = "█" * filled + "░" * (bar_w - filled)
            addline(f"  Memory  [{bar}] {mem_pct:.0f}%")
            addline(f"          {mem['used_mb']}MB used / {mem['total_mb']}MB total")
            addline(f"  CPU     {cpu:.1f}%")
            addline("")

            # Section: Storage
            addline("  STORAGE", c.color_pair(3) | c.A_BOLD)
            disk_pct = disk["percent"]
            filled   = int(bar_w * disk_pct / 100)
            bar      = "█" * filled + "░" * (bar_w - filled)
            addline(f"  Disk    [{bar}] {disk_pct:.0f}%")
            addline(f"          {disk['used_mb']}MB used / {disk['total_mb']}MB total")

        except Exception as e:
            try:
                win.addnstr(y, x, f"  Error: {e}", width - 1)
            except Exception:
                pass
