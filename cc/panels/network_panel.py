"""CC Panel: Network / AIM."""


class NetworkPanel:
    TITLE = "NETWORK / AIM"

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
            # AIM status
            try:
                from aim.aim import get_aim
                aim    = get_aim()
                status = aim.get_status()
                online = status["online"]
            except Exception:
                online = False
                status = {"queued": 0, "version": "?"}

            addline("  AIM — ADAPTIVE INTERFACE MESH", c.color_pair(3) | c.A_BOLD)
            o_attr = c.color_pair(5) if online else c.color_pair(6)
            addline(f"  Status  : {'ONLINE' if online else 'OFFLINE'}", o_attr)
            addline(f"  Queued  : {status.get('queued', 0)} request(s)")
            addline(f"  Version : {status.get('version', '?')}")
            addline("")

            # Network interfaces
            addline("  NETWORK INTERFACES", c.color_pair(3) | c.A_BOLD)
            if kal:
                net_info = kal.get_network_info()
                ifaces   = net_info.get("interfaces", [])
                if ifaces:
                    for iface in ifaces:
                        addline(f"  {iface['name']:<16} {iface['ip']}")
                else:
                    addline("  No active interfaces detected.")
            addline("")

            # AIM commands hint
            addline("  ARROW COMMANDS", c.A_BOLD)
            addline("  aim status        — connectivity status")
            addline("  aim check         — force connectivity check")
            addline("  aim fetch <url>   — fetch URL via AIM")

        except Exception as e:
            try:
                win.addnstr(y, x, f"  Error: {e}", width - 1)
            except Exception:
                pass
