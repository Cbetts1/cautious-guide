"""CC Panel: Services — AIOS-managed services."""
import os


class ServicesPanel:
    TITLE = "SERVICES"

    def render(self, win, y: int, x: int, height: int, width: int,
               kal=None, curses_mod=None):
        c = curses_mod
        if kal is None:
            return
        try:
            procs = kal.list_processes()
            row = y

            def addline(text, attr=0):
                nonlocal row
                if row < y + height - 1:
                    try:
                        win.addnstr(row, x, text, width - 1, attr)
                    except Exception:
                        pass
                    row += 1

            addline("  AIOS MANAGED SERVICES", c.color_pair(3) | c.A_BOLD)
            addline(f"  Running: {kal.proc_registry.running_count()} / "
                    f"{kal.proc_registry.total_count()}")
            addline("")

            if not procs:
                addline("  No AIOS services registered.")
                addline("")
                addline("  Services auto-start from config/aios.cfg")
                addline("  Use ARROW: 'services' to list at runtime.")
            else:
                hdr = f"  {'NAME':<18} {'PID':<8} {'STATUS':<10} {'STARTED'}"
                addline(hdr, c.A_BOLD)
                addline("  " + "─" * (width - 4))
                for p in procs:
                    status = p.get("status", "unknown")
                    attr   = c.color_pair(5) if status == "running" else c.color_pair(6)
                    line   = (f"  {p['name']:<18} {p['pid']:<8} "
                              f"{status:<10} {p['started_at']}")
                    addline(line)

            addline("")
            addline("  QUICK ACTIONS", c.A_BOLD)
            addline("  [S] Launch ARROW shell to manage services")
            addline("  arrow build service <name>  — create new service")

        except Exception as e:
            try:
                win.addnstr(y, x, f"  Error: {e}", width - 1)
            except Exception:
                pass
