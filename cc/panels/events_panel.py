"""
CC Panel: Events — Live System Event Log

Shows recent events from the AIOS EventBus with timestamps,
source labels, severity levels, and messages.
Supports UP/DOWN scrolling through event history.
"""

# Color pair IDs (must match cc/command_center.py)
_CP_CYAN   = 1
_CP_WHITE  = 2
_CP_SEL    = 3
_CP_GREEN  = 5
_CP_RED    = 6
_CP_YELLOW = 7
_CP_BLUE   = 8

_LEVEL_LABELS = {
    "OK":    " OK",
    "INFO":  "INF",
    "WARN":  "WRN",
    "ERROR": "ERR",
}


class EventsPanel:
    TITLE = "EVENTS"

    def __init__(self):
        self._scroll = 0   # rows from the bottom (0 = most recent at bottom)

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
            from cc.events import get_event_bus, LEVEL_OK, LEVEL_WARN, LEVEL_ERROR

            bus    = get_event_bus()
            all_ev = bus.all()
            total  = len(all_ev)

            # Header
            addline(f"  LIVE EVENT LOG                         {total} event(s) total",
                    c.color_pair(_CP_CYAN) | c.A_BOLD)
            addline("  ── Timestamp · Level · Source · Message ─────────────────",
                    c.color_pair(_CP_BLUE))

            # Visible rows = height - header(2) - footer(2)
            visible  = max(1, height - 4)
            max_scroll = max(0, total - visible)
            self._scroll = min(self._scroll, max_scroll)
            self._scroll = max(0, self._scroll)

            # Slice: scroll=0 means show tail; scroll=N means N rows from bottom
            start = max(0, total - visible - self._scroll)
            end   = start + visible
            shown = all_ev[start:end]

            if not shown:
                addline("")
                addline("  No events recorded yet.")
                addline("  Events appear here as the system runs.")
                addline("  Boot, layer state changes, and network events are logged.")
            else:
                for ev in shown:
                    lvl_tag = _LEVEL_LABELS.get(ev.level, ev.level[:3])

                    if ev.level == LEVEL_ERROR:
                        ev_attr = c.color_pair(_CP_RED)
                    elif ev.level == LEVEL_WARN:
                        ev_attr = c.color_pair(_CP_YELLOW)
                    elif ev.level == LEVEL_OK:
                        ev_attr = c.color_pair(_CP_GREEN)
                    else:
                        ev_attr = 0

                    max_msg = max(8, width - 34)
                    msg     = ev.message[:max_msg]
                    src     = ev.source[:9]
                    addline(f"  {ev.ts_str()}  {lvl_tag}  [{src:<9}]  {msg}", ev_attr)

            # Footer / scroll hint
            footer_row = y + height - 2
            if footer_row > row:
                row = footer_row
            scroll_hint = ""
            if self._scroll > 0:
                scroll_hint = f"  ↑ older   ↓ newer   scroll:{self._scroll}"
            elif max_scroll > 0:
                scroll_hint = "  ↑ scroll up for history"
            else:
                scroll_hint = "  — end of log —"
            addline("  ─────────────────────────────────────────────────────────",
                    c.color_pair(_CP_BLUE))
            addline(scroll_hint, c.color_pair(_CP_WHITE) | c.A_DIM)

        except Exception as e:
            try:
                win.addnstr(y + 1, x,
                            f"  Events error: {e}", max(1, width - 1),
                            c.color_pair(_CP_RED))
            except Exception:
                pass

    def handle_key(self, key, curses_mod=None):
        """Scroll through event history with UP/DOWN arrow keys."""
        c = curses_mod
        if key == (c.KEY_UP if c else 259):
            self._scroll = max(0, self._scroll + 1)
        elif key == (c.KEY_DOWN if c else 258):
            self._scroll = max(0, self._scroll - 1)
        elif key in (ord("r"), ord("R")):
            self._scroll = 0   # jump to most recent
