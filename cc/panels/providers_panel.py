"""CC Panel: Providers — view and manage registered backend providers."""


class ProvidersPanel:
    TITLE = "PROVIDERS"

    def __init__(self):
        self._sel = 0
        self._msg = ""

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
            from providers.base import get_provider_registry, FEAT_MESSAGING, \
                FEAT_VOICE, FEAT_REMOTE, FEAT_DEPLOY, FEAT_CLOUD
            from comms.base import get_comms_manager
            from remote.base import get_remote_manager

            pr   = get_provider_registry()
            cm   = get_comms_manager()
            rm   = get_remote_manager()

            all_providers = pr.list_all()

            addline("  AIOS PROVIDER REGISTRY", c.color_pair(1) | c.A_BOLD)
            addline(f"  {pr.count()} provider(s) registered   | {self._msg}",
                    c.color_pair(2))
            addline("  " + "─" * (width - 4), c.color_pair(8))
            addline("")

            if not all_providers:
                addline("  No providers registered yet.", c.color_pair(7))
                addline("")
                addline("  Providers are pluggable backends for:", c.A_BOLD)
                addline("    ◈ Messaging  (SMS, app relay, XMPP…)")
                addline("    ◈ Voice      (VoIP, WebRTC, SIP…)")
                addline("    ◈ Remote     (SSH, HTTP API, container…)")
                addline("    ◈ Deploy     (cloud push, rsync, CI/CD…)")
                addline("    ◈ Cloud      (AWS, GCP, custom…)")
                addline("")
                addline("  Register a provider programmatically:", c.A_BOLD)
                addline("    from providers.base import (")
                addline("        MessagingProvider, get_provider_registry)")
                addline("    class MyProvider(MessagingProvider): ...")
                addline("    p = MyProvider(); p.name = 'my-sms'")
                addline("    get_provider_registry().register(p)")
                addline("")
                addline("  Then wire it into the comms or remote manager:", c.A_BOLD)
                addline("    from comms.base import get_comms_manager")
                addline("    get_comms_manager().register_provider(p)")
                return

            # Clamp selection
            if self._sel >= len(all_providers):
                self._sel = max(0, len(all_providers) - 1)

            hdr = f"  {'NAME':<20} {'FEATURES':<28} STATUS"
            addline(hdr, c.A_BOLD)
            addline("  " + "─" * (width - 4), c.color_pair(8))

            for i, p in enumerate(all_providers):
                is_sel   = (i == self._sel)
                connected = p.is_connected()
                status    = "◉ connected" if connected else "○ offline"
                sc        = 5 if connected else 8
                attr      = (c.color_pair(3) | c.A_BOLD | c.A_REVERSE) if is_sel \
                    else c.color_pair(sc)
                feats     = ", ".join(sorted(p.features))[:26]
                line      = f"  {p.name:<20} {feats:<28} {status}"
                addline(line[:width - 2], attr)

            # Detail pane
            if all_providers and self._sel < len(all_providers):
                p = all_providers[self._sel]
                addline("")
                addline("  SELECTED PROVIDER", c.A_BOLD)
                addline(f"    Name      : {p.name}")
                addline(f"    Features  : {', '.join(sorted(p.features))}")
                addline(f"    Connected : {p.is_connected()}")
                health = p.health_check()
                h_attr = c.color_pair(5) if health.get("ok") else c.color_pair(6)
                addline(f"    Health    : {health.get('message', '—')}", h_attr)

        except Exception as e:
            try:
                win.addnstr(y, x, f"  Providers panel error: {e}", width - 1,
                            curses_mod.color_pair(6) if curses_mod else 0)
            except Exception:
                pass

    def handle_key(self, key, curses_mod=None):
        c = curses_mod
        if key == c.KEY_UP:
            self._sel = max(0, self._sel - 1)
            self._msg = ""
        elif key == c.KEY_DOWN:
            self._sel += 1
            self._msg = ""
