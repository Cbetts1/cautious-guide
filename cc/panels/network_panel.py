"""CC Panel: Network / AIM — Adaptive Interface Mesh control surface."""
import time


class NetworkPanel:
    TITLE = "NETWORK / AIM"

    def __init__(self):
        self._last_check_ts = None   # timestamp of last manual check

    def render(self, win, y: int, x: int, height: int, width: int,
               kal=None, curses_mod=None):
        c   = curses_mod
        row = y

        def addline(text="", attr=0):
            nonlocal row
            if row < y + height - 1:
                try:
                    win.addnstr(row, x, str(text), max(1, width - 1), attr)
                except Exception:
                    pass
                row += 1

        try:
            # ── AIM bridge status ─────────────────────────────────────────────
            try:
                from aim.aim import get_aim
                aim    = get_aim()
                status = aim.get_status()
                online = status["online"]
            except Exception:
                online = False
                status = {"queued": 0, "version": "?", "enabled": False,
                          "proxy_enabled": False}

            addline("  AIM — ADAPTIVE INTERFACE MESH", c.color_pair(3) | c.A_BOLD)
            o_attr   = c.color_pair(5) if online else c.color_pair(6)
            o_label  = "ONLINE" if online else "OFFLINE"
            addline(f"  Status  : {o_label}", o_attr)
            addline(f"  Version : {status.get('version', '?')}")
            addline(f"  Enabled : {'Yes' if status.get('enabled', True) else 'No'}")
            addline(f"  Queued  : {status.get('queued', 0)} pending request(s)")
            addline(f"  Proxy   : {'Enabled' if status.get('proxy_enabled') else 'Disabled'}")
            if self._last_check_ts:
                age = int(time.time() - self._last_check_ts)
                addline(f"  Checked : {age}s ago")
            addline("")

            # ── Network interfaces ────────────────────────────────────────────
            addline("  NETWORK INTERFACES", c.color_pair(3) | c.A_BOLD)
            if kal:
                net_info = kal.get_network_info()
                ifaces   = net_info.get("interfaces", [])
                if ifaces:
                    for iface in ifaces:
                        attr = c.color_pair(5) if not iface["name"].startswith("lo") else 0
                        addline(f"  {iface['name']:<18} {iface['ip']}", attr)
                else:
                    addline("  No active interfaces detected.", c.color_pair(7))
            addline("")

            # ── Quick actions ─────────────────────────────────────────────────
            addline("  QUICK ACTIONS", c.A_BOLD)
            addline("  [C]  Force connectivity check now")
            addline("  [F]  Flush offline queue (retry queued requests)")
            addline("")

            # ── ARROW commands reference ──────────────────────────────────────
            addline("  ARROW COMMANDS", c.A_BOLD)
            addline("  aim status          — bridge + connectivity status")
            addline("  aim check           — force connectivity check")
            addline("  aim fetch <url>     — fetch URL via AIM")

        except Exception as e:
            try:
                win.addnstr(y, x, f"  Error: {e}", max(1, width - 1))
            except Exception:
                pass

    def handle_key(self, key, curses_mod=None):
        """Handle panel key actions."""
        if key in (ord("c"), ord("C")):
            try:
                from aim.aim import get_aim
                from cc.events import get_event_bus, LEVEL_OK, LEVEL_WARN
                online = get_aim().check_now()
                self._last_check_ts = time.time()
                bus = get_event_bus()
                if online:
                    bus.emit("AIM", LEVEL_OK, "Manual check: network ONLINE")
                else:
                    bus.emit("AIM", LEVEL_WARN, "Manual check: network OFFLINE")
            except Exception:
                pass

        elif key in (ord("f"), ord("F")):
            try:
                from aim.aim import get_aim
                from cc.events import get_event_bus, LEVEL_INFO
                aim = get_aim()
                q   = len(aim._queue)
                aim._flush_queue()
                get_event_bus().emit("AIM", LEVEL_INFO,
                                     f"Queue flushed — {q} request(s) replayed")
            except Exception:
                pass
