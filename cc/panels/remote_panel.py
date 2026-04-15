"""CC Panel: Remote — connect to and control remote systems."""


class RemotePanel:
    TITLE = "REMOTE"

    def __init__(self):
        self._sel = 0
        self._msg = ""
        self._tab = "hosts"   # hosts | providers

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
            from remote.base import get_remote_manager
            rm    = get_remote_manager()
            hosts = rm.list_hosts()

            addline("  AIOS REMOTE CONTROL", c.color_pair(1) | c.A_BOLD)
            tab_line = "  "
            for t in ("hosts", "providers"):
                tab_line += f"[{t.upper()}]  " if t == self._tab else f" {t}   "
            addline(tab_line, c.color_pair(2))
            addline(f"  H=Hosts  P=Providers  C=Connect  D=Disconnect  | {self._msg}",
                    c.color_pair(8))
            addline("  " + "─" * (width - 4), c.color_pair(8))
            addline("")

            if self._tab == "hosts":
                self._render_hosts(addline, rm, hosts, c, width)
            else:
                self._render_providers(addline, rm, c)

        except Exception as e:
            try:
                win.addnstr(y, x, f"  Remote panel error: {e}", width - 1,
                            curses_mod.color_pair(6) if curses_mod else 0)
            except Exception:
                pass

    def _render_hosts(self, addline, rm, hosts, c, width):
        addline(f"  REMOTE HOSTS  ({len(hosts)})", c.A_BOLD)
        if not hosts:
            addline("  No remote hosts configured.")
            addline("")
            addline("  Remote hosts are systems you can connect to,")
            addline("  deploy to, and control from the hub.")
            addline("")
            addline("  Add a host programmatically via:")
            addline("    from remote.base import get_remote_manager")
            addline("    rm = get_remote_manager()")
            addline("    rm.add_host('my-vps', '192.168.1.10')")
            addline("")
            addline("  Providers: SSH, API, container, custom agent.")
            return

        # Clamp selection
        if self._sel >= len(hosts):
            self._sel = max(0, len(hosts) - 1)

        hdr = f"  {'NAME':<16} {'HOST':<20} {'STATUS':<14} SYNC"
        addline(hdr, c.A_BOLD)
        addline("  " + "─" * (width - 4), c.color_pair(8))

        _status_colors = {
            "connected":    5,
            "connecting":   7,
            "disconnected": 8,
            "error":        6,
        }

        for i, h in enumerate(hosts):
            is_sel      = (i == self._sel)
            sc          = _status_colors.get(h.status, 2)
            attr        = (c.color_pair(3) | c.A_BOLD | c.A_REVERSE) if is_sel \
                else c.color_pair(sc)
            sync        = (h.last_sync or "never")[:16]
            line = f"  {h.name:<16} {h.host:<20} {h.status:<14} {sync}"
            addline(line[:width - 2], attr)

        # Detail for selected host
        if hosts and self._sel < len(hosts):
            h = hosts[self._sel]
            addline("")
            addline("  SELECTED HOST", c.A_BOLD)
            addline(f"    Name     : {h.name}")
            addline(f"    Host     : {h.host}:{h.port}")
            addline(f"    Provider : {h.provider_name or '(none)'}")
            addline(f"    Status   : {h.status}")
            addline(f"    Added    : {h.added_at[:16]}")

    def _render_providers(self, addline, rm, c):
        addline("  REMOTE PROVIDERS", c.A_BOLD)
        addline("")
        providers_list = list(rm._providers.values())
        if not providers_list:
            addline("  No remote providers registered.")
            addline("")
            addline("  Providers supply the transport for remote control.")
            addline("  Future: SSH, HTTP API, container exec, custom relay.")
            addline("")
            addline("  Register via:")
            addline("    from remote.base import get_remote_manager")
            addline("    from providers.base import RemoteProvider")
        else:
            for p in providers_list:
                status = "◉" if p.is_connected() else "○"
                attr   = c.color_pair(5) if p.is_connected() else c.color_pair(8)
                addline(f"  {status} {p.name}", attr)

    def handle_key(self, key, curses_mod=None):
        c = curses_mod
        if key in (ord("h"), ord("H")):
            self._tab = "hosts"
            self._msg = ""
        elif key in (ord("p"), ord("P")):
            self._tab = "providers"
            self._msg = ""
        elif key == c.KEY_UP:
            self._sel = max(0, self._sel - 1)
            self._msg = ""
        elif key == c.KEY_DOWN:
            self._sel += 1
            self._msg = ""
        elif key in (ord("c"), ord("C")):
            try:
                from remote.base import get_remote_manager
                rm    = get_remote_manager()
                hosts = rm.list_hosts()
                if hosts and self._sel < len(hosts):
                    result = rm.connect(hosts[self._sel].name)
                    self._msg = result.get("message", "")
                else:
                    self._msg = "No host selected."
            except Exception as e:
                self._msg = str(e)
        elif key in (ord("d"), ord("D")):
            try:
                from remote.base import get_remote_manager
                rm    = get_remote_manager()
                hosts = rm.list_hosts()
                if hosts and self._sel < len(hosts):
                    result = rm.disconnect(hosts[self._sel].name)
                    self._msg = result.get("message", "")
                else:
                    self._msg = "No host selected."
            except Exception as e:
                self._msg = str(e)
