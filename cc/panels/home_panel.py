"""
CC Panel: Home — AIOS Command Center Dashboard

The primary overview experience. Shows live system health,
active layer status, recent events, and quick action shortcuts.
"""

import os
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Color pair IDs (must match cc/command_center.py)
_CP_CYAN   = 1
_CP_WHITE  = 2
_CP_SEL    = 3   # black on cyan — used as section header highlight
_CP_GREEN  = 5
_CP_RED    = 6
_CP_YELLOW = 7
_CP_BLUE   = 8


class HomePanel:
    TITLE = "HOME"

    def render(self, win, y: int, x: int, height: int, width: int,
               kal=None, curses_mod=None):
        c   = curses_mod
        row = y

        def addline(text="", attr=0):
            nonlocal row
            if row >= y + height - 1:
                return
            try:
                win.addnstr(row, x, str(text), max(1, width - 1), attr)
            except Exception:
                pass
            row += 1

        try:
            ts = time.strftime("%H:%M:%S")

            # ── Banner ────────────────────────────────────────────────────────
            ts_pad  = " " * max(0, width - 28 - len(ts))
            addline(f"  AIOS COMMAND CENTER{ts_pad}{ts} ",
                    c.color_pair(_CP_SEL) | c.A_BOLD)
            addline("  ─────────────────────────────────────────────────────────",
                    c.color_pair(_CP_BLUE))

            # ── System Health (compact) ───────────────────────────────────────
            uptime = "?"
            health_lbl  = "● HEALTHY"
            health_attr = c.color_pair(_CP_GREEN) | c.A_BOLD
            mem_pct = cpu_pct = disk_pct = 0

            if kal:
                try:
                    mem    = kal.get_memory()
                    cpu    = kal.get_cpu_percent()
                    disk   = kal.get_disk_usage(ROOT)
                    uptime = kal.get_uptime_str()
                    mem_pct  = mem["percent"]
                    cpu_pct  = cpu
                    disk_pct = disk["percent"]

                    if mem_pct > 90 or cpu_pct > 90:
                        health_lbl  = "● CRITICAL"
                        health_attr = c.color_pair(_CP_RED) | c.A_BOLD
                    elif mem_pct > 70 or cpu_pct > 70:
                        health_lbl  = "◑ STRESSED"
                        health_attr = c.color_pair(_CP_YELLOW) | c.A_BOLD

                    bw = max(10, min(20, (width - 50) // 2))

                    def _bar(pct):
                        f = int(bw * pct / 100)
                        return "█" * f + "░" * (bw - f)

                    def _ba(pct):
                        if pct > 80: return c.color_pair(_CP_RED)
                        if pct > 60: return c.color_pair(_CP_YELLOW)
                        return c.color_pair(_CP_GREEN)

                    addline(f"  {health_lbl}   uptime:{uptime}", health_attr)
                    addline(f"  RAM[{_bar(mem_pct)}]{mem_pct:.0f}%  "
                            f"CPU[{_bar(cpu_pct)}]{cpu_pct:.0f}%  "
                            f"DSK[{_bar(disk_pct)}]{disk_pct:.0f}%",
                            _ba(max(mem_pct, cpu_pct)))

                except Exception:
                    addline("  System stats unavailable.", c.color_pair(_CP_YELLOW))

            # ── Active Layers (compact) ───────────────────────────────────────
            addline("  ─── LAYERS ──────────────────────────────────────────────",
                    c.color_pair(_CP_BLUE))

            kal_dot  = "●" if kal else "○"
            kal_attr = c.color_pair(_CP_GREEN) if kal else c.color_pair(_CP_RED)
            addline(f"  {kal_dot} KAL   ● ARROW   ● CC", kal_attr)

            aim_online = False
            aim_queued = 0
            try:
                from aim.aim import get_aim
                ai         = get_aim()
                st         = ai.get_status()
                aim_online = st["online"]
                aim_queued = st["queued"]
            except Exception:
                pass
            aim_dot  = "●" if aim_online else "○"
            aim_lbl  = "ONLINE " if aim_online else "OFFLINE"
            aim_attr = c.color_pair(_CP_GREEN) if aim_online else c.color_pair(_CP_YELLOW)
            q_note   = f" q:{aim_queued}" if aim_queued else ""

            aura_mode = "?"
            try:
                from ai.aura import get_aura
                aura_mode = get_aura().get_status()["mode"]
            except Exception:
                pass

            addline(f"  {aim_dot} AIM:{aim_lbl}{q_note}   ● AURA:{aura_mode}",
                    aim_attr)

            svc_run = svc_total = plug_count = 0
            if kal:
                try:
                    svc_run   = kal.proc_registry.running_count()
                    svc_total = kal.proc_registry.total_count()
                except Exception:
                    pass
            try:
                plug_dir   = os.path.join(ROOT, "plugins", "installed")
                plug_count = len([d for d in os.listdir(plug_dir)
                                  if os.path.isdir(os.path.join(plug_dir, d))])
            except Exception:
                pass
            addline(f"  ◈ Plugins:{plug_count}   Services:{svc_run}/{svc_total}",
                    c.color_pair(_CP_WHITE))

            # ── Recent Events ─────────────────────────────────────────────────
            addline("  ─── RECENT EVENTS ───────────────────────────────────────",
                    c.color_pair(_CP_BLUE))
            try:
                from cc.events import get_event_bus, LEVEL_OK, LEVEL_WARN, LEVEL_ERROR
                events = get_event_bus().recent(4)
                if events:
                    for ev in reversed(events):
                        if ev.level == LEVEL_ERROR:
                            ev_attr = c.color_pair(_CP_RED)
                            lvl_tag = "ERR"
                        elif ev.level == LEVEL_WARN:
                            ev_attr = c.color_pair(_CP_YELLOW)
                            lvl_tag = "WRN"
                        elif ev.level == LEVEL_OK:
                            ev_attr = c.color_pair(_CP_GREEN)
                            lvl_tag = " OK"
                        else:
                            ev_attr = 0
                            lvl_tag = "INF"
                        max_msg = max(8, width - 33)
                        msg     = ev.message[:max_msg]
                        src     = ev.source[:8]
                        addline(f"  {ev.ts_str()}  {lvl_tag}  {src:<8}  {msg}",
                                ev_attr)
                else:
                    addline("  System starting — events will appear here.",
                            c.color_pair(_CP_WHITE) | c.A_DIM)
            except Exception:
                addline("  Events unavailable.", c.color_pair(_CP_YELLOW))

            # ── Quick Actions ─────────────────────────────────────────────────
            addline("  ─── QUICK ACTIONS ───────────────────────────────────────",
                    c.color_pair(_CP_BLUE))
            addline("  [1]Home [2]Sys [3]Layers [4]ARROW [5]Svc [6]AURA",
                    c.color_pair(_CP_CYAN))
            addline("  [7]Net  [8]Evts [9]Stor  ↑/↓ nav  Enter  Q quit",
                    c.color_pair(_CP_CYAN))

        except Exception as e:
            try:
                win.addnstr(y + 1, x,
                            f"  Dashboard error: {e}", max(1, width - 1),
                            c.color_pair(_CP_RED))
            except Exception:
                pass
