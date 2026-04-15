"""CC Panel: Events — scrollable live event log from the AIOS EventBus."""


class EventsPanel:
    TITLE = "EVENTS"

    def __init__(self):
        self._scroll   = 0   # offset from bottom (0 = show latest)
        self._filter   = None  # None = all, or level string

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
            from cc.events import get_event_bus, LEVEL_OK, LEVEL_WARN, LEVEL_ERROR, LEVEL_INFO
            bus = get_event_bus()
            events = bus.get_events(500)

            filter_str = f"  filter: {self._filter}" if self._filter else "  filter: all"
            addline("  AIOS EVENT LOG" + " " * 4 + filter_str,
                    c.color_pair(3) | c.A_BOLD)
            addline(f"  {bus.count()} total events   ↑/↓ scroll   F filter   C clear",
                    c.color_pair(2))
            addline("  " + "─" * (width - 4))

            content_h = height - 4   # rows available for events
            # Apply scroll offset
            total = len(events)
            max_scroll = max(0, total - content_h)
            self._scroll = max(0, min(self._scroll, max_scroll))
            start = max(0, total - content_h - self._scroll)
            visible = events[start: start + content_h]

            level_colors = {
                LEVEL_OK:    c.color_pair(5),   # green
                LEVEL_WARN:  c.color_pair(7),   # yellow
                LEVEL_ERROR: c.color_pair(6),   # red
                LEVEL_INFO:  c.color_pair(8),   # blue
            }

            if not visible:
                addline("  No events recorded yet.")
            for ev in visible:
                color = level_colors.get(ev.level, c.color_pair(2))
                line = f"  [{ev.ts_str}] [{ev.level:<5}] {ev.source}: {ev.message}"
                addline(line[:width - 2], color)

        except Exception as e:
            try:
                win.addnstr(y, x, f"  Events panel error: {e}", width - 1)
            except Exception:
                pass

    def handle_key(self, key, curses_mod=None):
        from cc.events import get_event_bus, LEVEL_WARN, LEVEL_ERROR, LEVEL_INFO
        if key == curses_mod.KEY_UP:
            self._scroll += 1
        elif key == curses_mod.KEY_DOWN:
            self._scroll = max(0, self._scroll - 1)
        elif key in (ord("c"), ord("C")):
            get_event_bus().clear()
            self._scroll = 0
        elif key in (ord("f"), ord("F")):
            # Cycle filter: None → ERROR → WARN → INFO → None
            cycle = [None, LEVEL_ERROR, LEVEL_WARN, LEVEL_INFO]
            try:
                idx = cycle.index(self._filter)
            except ValueError:
                idx = 0
            self._filter = cycle[(idx + 1) % len(cycle)]
