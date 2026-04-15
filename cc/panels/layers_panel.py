"""
CC Panel: Layers — AIOS Layer Manager

Shows the status, health, version, description, and available actions
for every active AIOS system layer: KAL, AIM, AURA, ARROW, CC, and Plugins.
Does NOT touch layer internals — reads only public status APIs.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Color pair IDs (must match cc/command_center.py)
_CP_CYAN   = 1
_CP_WHITE  = 2
_CP_SEL    = 3
_CP_GREEN  = 5
_CP_RED    = 6
_CP_YELLOW = 7
_CP_BLUE   = 8


class LayersPanel:
    TITLE = "LAYERS"

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

        def skip():
            nonlocal row
            row += 1

        def section(title):
            addline(f"  {title}", c.color_pair(_CP_SEL) | c.A_BOLD)

        def item(label, value, attr=0):
            addline(f"    ├─ {label:<14} {value}", attr)

        def item_last(label, value, attr=0):
            addline(f"    └─ {label:<14} {value}", attr)

        try:
            addline("  AIOS SYSTEM LAYERS", c.color_pair(_CP_CYAN) | c.A_BOLD)
            addline("  ── Status · Health · Version · Role ──────────────────────",
                    c.color_pair(_CP_BLUE))

            # ── KAL ───────────────────────────────────────────────────────────
            skip()
            if kal:
                section("● KAL  — Kernel Abstraction Layer")
                pi   = kal.get_platform_info()
                mem  = kal.get_memory()
                cpu  = kal.get_cpu_percent()
                uptime = kal.get_uptime_str()

                if mem["percent"] > 90 or cpu > 90:
                    health_lbl  = "STRESSED"
                    health_attr = c.color_pair(_CP_YELLOW)
                else:
                    health_lbl  = "NOMINAL"
                    health_attr = c.color_pair(_CP_GREEN)

                item("Version",     "v1.0.0",     c.color_pair(_CP_WHITE))
                item("Status",      "ACTIVE",      c.color_pair(_CP_GREEN))
                item("Health",      health_lbl,    health_attr)
                item("Uptime",      uptime,        c.color_pair(_CP_WHITE))
                item("Platform",    f"{pi['system']} {pi['machine']}", c.color_pair(_CP_WHITE))
                item_last("Role",   "OS resource interface — swap-ready")
            else:
                section("○ KAL  — Kernel Abstraction Layer")
                item_last("Status", "UNAVAILABLE", c.color_pair(_CP_RED))

            # ── AIM ───────────────────────────────────────────────────────────
            skip()
            aim_online = False
            aim_queued = 0
            aim_version = "?"
            aim_enabled = True
            try:
                from aim.aim import get_aim
                aim_inst   = get_aim()
                st         = aim_inst.get_status()
                aim_online  = st["online"]
                aim_queued  = st["queued"]
                aim_version = st["version"]
                aim_enabled = st["enabled"]
            except Exception:
                aim_enabled = False

            aim_dot = "●" if aim_online else "○"
            aim_lbl = "ONLINE" if aim_online else "OFFLINE"
            if aim_enabled:
                section(f"{aim_dot} AIM  — Adaptive Interface Mesh")
                aim_attr = c.color_pair(_CP_GREEN) if aim_online else c.color_pair(_CP_YELLOW)
                item("Version",  f"v{aim_version}")
                item("Status",   aim_lbl,  aim_attr)
                item("Health",   "NOMINAL" if aim_online else "DEGRADED",
                     c.color_pair(_CP_GREEN) if aim_online else c.color_pair(_CP_YELLOW))
                item("Queue",    f"{aim_queued} pending request(s)")
                item("Actions",  "aim check · aim fetch <url> · aim status",
                     c.color_pair(_CP_CYAN))
                item_last("Role", "HTTP bridge — online gateway / offline queue")
            else:
                section("○ AIM  — Adaptive Interface Mesh")
                item_last("Status", "DISABLED", c.color_pair(_CP_YELLOW))

            # ── AURA ──────────────────────────────────────────────────────────
            skip()
            aura_ok    = False
            aura_mode  = "unavailable"
            aura_rules = 0
            aura_ctx   = 0
            aura_ver   = "?"
            try:
                from ai.aura import get_aura
                st2        = get_aura().get_status()
                aura_ok    = True
                aura_mode  = st2["mode"]
                aura_rules = st2["rules"]
                aura_ctx   = st2["ctx_items"]
                aura_ver   = st2["version"]
            except Exception:
                pass

            aura_dot = "●" if aura_ok else "○"
            if aura_ok:
                section(f"● AURA — Autonomous Universal Reasoning")
                item("Version",     f"v{aura_ver}")
                item("Status",      "ACTIVE",  c.color_pair(_CP_GREEN))
                item("Mode",        aura_mode.upper(), c.color_pair(_CP_CYAN))
                item("Rules",       f"{aura_rules} loaded")
                item("Context",     f"{aura_ctx} item(s)")
                item("Actions",     "aura <question>  in ARROW shell",
                     c.color_pair(_CP_CYAN))
                item_last("Role",   "AI engine — rule-based now, LLM-ready")
            else:
                section("○ AURA — Autonomous Universal Reasoning")
                item_last("Status", "INIT DEFERRED", c.color_pair(_CP_YELLOW))

            # ── ARROW ─────────────────────────────────────────────────────────
            skip()
            section("● ARROW — Autonomous Routing Relay Orchestration Workflow")
            item("Version",  "v1.0.0")
            item("Status",   "READY",    c.color_pair(_CP_GREEN))
            item("Health",   "NOMINAL",  c.color_pair(_CP_GREEN))
            item("Access",   "Press Enter on 'ARROW Shell' menu item",
                 c.color_pair(_CP_CYAN))
            item("Actions",  "All Linux/Termux cmds + AIOS built-ins",
                 c.color_pair(_CP_WHITE))
            item_last("Role", "Command execution / routing / build system")

            # ── Plugins ───────────────────────────────────────────────────────
            skip()
            plug_dir   = os.path.join(ROOT, "plugins", "installed")
            plug_names = []
            try:
                plug_names = [d for d in os.listdir(plug_dir)
                              if os.path.isdir(os.path.join(plug_dir, d))]
            except Exception:
                pass

            plug_dot = "●" if plug_names else "◈"
            section(f"{plug_dot} PLUGINS — Optional Extensions "
                    f"({len(plug_names)} installed)")
            if plug_names:
                for i, pname in enumerate(plug_names[:4]):
                    fn = item_last if i == len(plug_names) - 1 or i == 3 else item
                    fn("Plugin", pname, c.color_pair(_CP_WHITE))
                if len(plug_names) > 4:
                    addline(f"    └─ ...and {len(plug_names) - 4} more")
            else:
                item_last("Hint",
                          "aios install <name> · aios list available",
                          c.color_pair(_CP_CYAN))

        except Exception as e:
            try:
                win.addnstr(y + 1, x,
                            f"  Layers error: {e}", max(1, width - 1),
                            c.color_pair(_CP_RED))
            except Exception:
                pass
