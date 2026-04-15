"""CC Panel: Studio Hub — home dashboard and quick actions."""
import os
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class HubPanel:
    TITLE = "STUDIO HUB"

    def render(self, win, y: int, x: int, height: int, width: int,
               kal=None, curses_mod=None):
        c = curses_mod
        row = y

        def addline(text, attr=0):
            nonlocal row
            if row < y + height - 1:
                try:
                    win.addnstr(row, x, text, width - 1, attr)
                except Exception:
                    pass
                row += 1

        try:
            from hub.device_profile import get_profile
            from hub.hub_state import get_hub_state
            profile = get_profile()
            state   = get_hub_state()

            addline("  ◈  AIOS STUDIO HUB", c.color_pair(1) | c.A_BOLD)
            addline(f"  Autonomous Intelligence Operating System  —  v1.0.0")
            addline("  " + "─" * (width - 4), c.color_pair(8))
            addline("")

            # ── Device profile ───────────────────────────────────────
            mode_colors = {
                "lite":     c.color_pair(7),   # yellow
                "balanced": c.color_pair(5),   # green
                "full":     c.color_pair(1),   # cyan
            }
            mode_attr = mode_colors.get(profile.mode, c.color_pair(2))
            addline(f"  Device mode : ", c.color_pair(2))
            # Write mode inline — use cursor position trick via separate addline
            row -= 1
            mode_label = profile.mode.upper()
            try:
                win.addnstr(row, x + 16, mode_label, width - 18, mode_attr | c.A_BOLD)
                win.addnstr(row, x + 16 + len(mode_label),
                            f"   (refresh {profile.refresh_sec}s)",
                            width - 18 - len(mode_label), c.color_pair(2))
            except Exception:
                pass
            row += 1

            # ── Stats overview ───────────────────────────────────────
            if kal:
                try:
                    mem = kal.get_memory()
                    cpu = kal.get_cpu_percent()
                    up  = kal.get_uptime_str()
                    addline(f"  Uptime      : {up}", c.color_pair(2))
                    mem_attr = (c.color_pair(6) if mem["percent"] > 80
                                else c.color_pair(7) if mem["percent"] > 60
                                else c.color_pair(5))
                    addline(f"  Memory      : {mem['used_mb']}/{mem['total_mb']}MB"
                            f"  ({mem['percent']:.0f}%)", mem_attr)
                    cpu_attr = (c.color_pair(6) if cpu > 80
                                else c.color_pair(7) if cpu > 60
                                else c.color_pair(5))
                    addline(f"  CPU         : {cpu:.1f}%", cpu_attr)
                except Exception as e:
                    addline(f"  Stats unavailable: {e}", c.color_pair(7))

            addline("")

            # ── Project summary ──────────────────────────────────────
            try:
                from projects.registry import get_registry
                reg   = get_registry()
                total = reg.count()
                running = len(reg.list_by_status("running"))
                last_pid = state.get("last_project")
                last_proj = reg.get(last_pid) if last_pid else None

                addline("  PROJECTS", c.A_BOLD)
                addline(f"    Total: {total}   Running: {running}")
                if last_proj:
                    addline(f"    Last : {last_proj['name']} [{last_proj['status']}]",
                            c.color_pair(1))
                else:
                    addline("    Use Projects panel to create your first project.")
            except Exception:
                addline("  PROJECTS", c.A_BOLD)
                addline("    Project registry unavailable.")

            addline("")

            # ── Communications summary ───────────────────────────────
            try:
                from comms.base import get_comms_manager
                cm      = get_comms_manager()
                unread  = cm.unread_count()
                in_call = cm.in_call()
                contacts = cm.contact_count()

                addline("  COMMUNICATIONS", c.A_BOLD)
                unread_attr = c.color_pair(7) if unread else c.color_pair(2)
                addline(f"    Messages: {unread} unread   Contacts: {contacts}",
                        unread_attr)
                if in_call:
                    addline("    ◉ CALL IN PROGRESS", c.color_pair(6) | c.A_BOLD)
                else:
                    prov_list = cm.list_providers()
                    if prov_list:
                        addline(f"    Providers: {len(prov_list)} configured")
                    else:
                        addline("    No providers configured  (Settings → Providers)")
            except Exception:
                addline("  COMMUNICATIONS", c.A_BOLD)
                addline("    Comms layer unavailable.")

            addline("")

            # ── Remote summary ───────────────────────────────────────
            try:
                from remote.base import get_remote_manager
                rm = get_remote_manager()
                hosts = rm.list_hosts()
                connected = [h for h in hosts if h.status == "connected"]

                addline("  REMOTE", c.A_BOLD)
                if hosts:
                    addline(f"    Hosts: {len(hosts)}   Connected: {len(connected)}")
                    for h in connected[:3]:
                        addline(f"    ◉ {h.name} ({h.host})", c.color_pair(5))
                else:
                    addline("    No remote hosts configured  (Remote panel)")
            except Exception:
                addline("  REMOTE", c.A_BOLD)
                addline("    Remote layer unavailable.")

            addline("")

            # ── Quick actions ────────────────────────────────────────
            addline("  QUICK ACTIONS", c.A_BOLD)
            addline("    ↑/↓ + Enter  Navigate menu panels")
            addline("    1-0          Jump directly to any panel")
            addline("    2 → Enter    Open ARROW shell")
            addline("    Q            Quit AIOS")
            addline("")
            addline(f"  {time.strftime('%Y-%m-%d  %H:%M:%S')}",
                    c.color_pair(8))

        except Exception as e:
            try:
                win.addnstr(y, x, f"  Hub panel error: {e}", width - 1,
                            curses_mod.color_pair(6) if curses_mod else 0)
            except Exception:
                pass
