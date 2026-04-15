"""CC Panel: Services — AIOS-managed services with live navigation."""
import os


class ServicesPanel:
    TITLE = "SERVICES"

    def __init__(self):
        self._sel = 0   # selected row index

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
                    f"{kal.proc_registry.total_count()}"
                    f"    ↑/↓ navigate  S stop  R refresh  Enter details")
            addline("")

            if not procs:
                addline("  No AIOS services registered.")
                addline("")
                addline("  Services auto-start from config/aios.cfg")
                addline("  Use ARROW: 'services' to list at runtime.")
                addline("  Use ARROW: 'aios run <plugin>' to start a service.")
            else:
                # Clamp selection
                if self._sel >= len(procs):
                    self._sel = max(0, len(procs) - 1)

                hdr = f"  {'NAME':<18} {'PID':<8} {'STATUS':<10} {'STARTED'}"
                addline(hdr, c.A_BOLD)
                addline("  " + "─" * (width - 4))
                for i, p in enumerate(procs):
                    status = p.get("status", "unknown")
                    is_sel = (i == self._sel)
                    base_attr = c.color_pair(5) if status == "running" else c.color_pair(6)
                    attr = (c.color_pair(3) | c.A_BOLD | c.A_REVERSE) if is_sel else base_attr
                    line = (f"  {p['name']:<18} {p['pid']:<8} "
                            f"{status:<10} {p['started_at']}")
                    addline(line, attr)

            addline("")
            addline("  QUICK ACTIONS", c.A_BOLD)
            addline("  [S] Stop selected   [R] Refresh   ARROW: aios run <name>")

        except Exception as e:
            try:
                win.addnstr(y, x, f"  Error: {e}", width - 1)
            except Exception:
                pass

    def handle_key(self, key, curses_mod=None):
        c = curses_mod
        from kernel.kal import get_kal
        try:
            procs = get_kal().list_processes()
        except Exception:
            procs = []

        if key == c.KEY_UP:
            self._sel = max(0, self._sel - 1)
        elif key == c.KEY_DOWN:
            self._sel = min(max(0, len(procs) - 1), self._sel + 1)
        elif key in (ord("s"), ord("S")):
            if procs and self._sel < len(procs):
                name = procs[self._sel]["name"]
                try:
                    from shell.commands.aios_cmds import _cmd_plugin_stop
                    _cmd_plugin_stop(name)
                    from cc.events import get_event_bus, LEVEL_INFO
                    get_event_bus().emit("services_panel", LEVEL_INFO, f"Stopped: {name}")
                except Exception:
                    pass
        elif key in (ord("r"), ord("R")):
            # Refresh — no-op, panel re-renders every cycle
            try:
                from cc.events import get_event_bus, LEVEL_INFO
                get_event_bus().emit("services_panel", LEVEL_INFO, "Services panel refreshed")
            except Exception:
                pass
