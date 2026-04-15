"""CC Panel: Communications — messages, calls, and contacts."""


class CommsPanel:
    TITLE = "MESSAGES"

    def __init__(self):
        self._tab = "messages"   # messages | calls | contacts | providers
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
            from comms.base import get_comms_manager
            cm = get_comms_manager()

            # Header
            addline("  AIOS COMMUNICATIONS", c.color_pair(1) | c.A_BOLD)
            tabs = ["messages", "calls", "contacts", "providers"]
            tab_line = "  "
            for t in tabs:
                if t == self._tab:
                    tab_line += f"[{t.upper()}]  "
                else:
                    tab_line += f" {t}   "
            addline(tab_line, c.color_pair(2))
            addline(f"  Tab switch: M=Messages  C=Calls  O=Contacts  P=Providers"
                    f"  | {self._msg}", c.color_pair(8))
            addline("  " + "─" * (width - 4), c.color_pair(8))
            addline("")

            if self._tab == "messages":
                self._render_messages(addline, cm, c, width)
            elif self._tab == "calls":
                self._render_calls(addline, cm, c)
            elif self._tab == "contacts":
                self._render_contacts(addline, cm, c, width)
            elif self._tab == "providers":
                self._render_providers(addline, cm, c)

        except Exception as e:
            try:
                win.addnstr(y, x, f"  Comms panel error: {e}", width - 1,
                            curses_mod.color_pair(6) if curses_mod else 0)
            except Exception:
                pass

    def _render_messages(self, addline, cm, c, width):
        messages = cm.get_messages(50)
        unread   = cm.unread_count()

        addline(f"  INBOX  ({unread} unread)", c.A_BOLD)
        if not messages:
            addline("  No messages yet.")
            addline("")
            addline("  To send a message, a messaging provider must be")
            addline("  configured. See Settings → Providers.")
            addline("")
            addline("  Supported in future: SMS, app messaging, relay.")
            return

        for m in reversed(messages[-15:]):
            arrow = "←" if m.direction == "in" else "→"
            attr  = c.color_pair(2)
            if m.direction == "in" and not m.read:
                attr = c.color_pair(7) | c.A_BOLD
            party = m.sender if m.direction == "in" else m.recipient
            line  = f"  [{m.ts_str}] {arrow} {party}: {m.body}"
            addline(line[:width - 2], attr)

        cm.mark_all_read()

    def _render_calls(self, addline, cm, c):
        addline("  CALLS", c.A_BOLD)
        if cm.in_call():
            addline("  ◉ CALL IN PROGRESS", c.color_pair(6) | c.A_BOLD)
            addline("")
            addline("  Press E to end the current call.")
        else:
            addline("  No active call.")
            addline("")
            addline("  To start a call, a voice provider must be")
            addline("  configured. See Settings → Providers.")
            addline("")
            addline("  Supported in future: VoIP, WebRTC, SIP relay.")

    def _render_contacts(self, addline, cm, c, width):
        contacts = cm.get_contacts()
        addline(f"  CONTACTS  ({len(contacts)})", c.A_BOLD)
        if not contacts:
            addline("  No contacts yet.")
            addline("")
            addline("  Contacts will appear here when added by a provider")
            addline("  or imported manually.")
            return
        for ct in contacts:
            status_color = c.color_pair(5) if ct.status == "online" else c.color_pair(8)
            line = f"  {ct.name:<20} {ct.handle:<20} {ct.status}"
            addline(line[:width - 2], status_color)

    def _render_providers(self, addline, cm, c):
        providers = cm.list_providers()
        addline(f"  COMMS PROVIDERS  ({len(providers)})", c.A_BOLD)
        if not providers:
            addline("  No providers registered.")
            addline("")
            addline("  Providers give the comms layer its backend.")
            addline("  Future providers: SMS gateway, VoIP, WebRTC,")
            addline("  custom relay, or a local stub for testing.")
            addline("")
            addline("  Register providers programmatically via:")
            addline("    from comms.base import get_comms_manager")
            addline("    from providers.base import MessagingProvider")
            return
        for p in providers:
            status = "◉ connected" if p.is_connected() else "○ offline"
            attr   = c.color_pair(5) if p.is_connected() else c.color_pair(8)
            addline(f"  {p.name:<20} {status}", attr)
            addline(f"    features: {', '.join(sorted(p.features))}")

    def handle_key(self, key, curses_mod=None):
        if key in (ord("m"), ord("M")):
            self._tab = "messages"
            self._msg = ""
        elif key in (ord("c"), ord("C")):
            self._tab = "calls"
            self._msg = ""
        elif key in (ord("o"), ord("O")):
            self._tab = "contacts"
            self._msg = ""
        elif key in (ord("p"), ord("P")):
            self._tab = "providers"
            self._msg = ""
        elif key in (ord("e"), ord("E")):
            try:
                from comms.base import get_comms_manager
                result = get_comms_manager().end_call()
                self._msg = result.get("message", "")
            except Exception as e:
                self._msg = str(e)
