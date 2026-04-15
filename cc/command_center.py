"""
AIOS Command Center
Modern Unicode TUI. Default launch target after boot + auth.
9-section sidebar menu, live status bar, panel content area.

Layout (minimum 80×22):
  ╔═══════ HEADER (3 rows) ═══════════════════════════════════╗
  ║ MENU (22w) ║ PANEL CONTENT AREA                          ║
  ║            ║                                             ║
  ╠════════════════ STATUS BAR (2 rows) ═══════════════════════╣
  ╚═══════════════════════════════════════════════════════════╝
"""

import curses
import os
import sys
import time
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ── Color pair IDs ────────────────────────────────────────────────────────────
CP_CYAN_BLK    = 1   # Cyan on black   — title, highlights
CP_WHITE_BLK   = 2   # White on black  — normal text
CP_BLK_CYAN    = 3   # Black on cyan   — selected item
CP_BLK_BLUE    = 4   # Black on blue   — status bar
CP_GREEN_BLK   = 5   # Green on black  — OK / running
CP_RED_BLK     = 6   # Red on black    — error / fail
CP_YELLOW_BLK  = 7   # Yellow on black — warning
CP_BLUE_BLK    = 8   # Blue on black   — borders / dim

MENU_WIDTH    = 22
HEADER_HEIGHT = 3
STATUS_HEIGHT = 2
MIN_WIDTH     = 80
MIN_HEIGHT    = 22

MENU_ITEMS = [
    ("◈ Home",       "home"),
    ("System",       "system"),
    ("Layers",       "layers"),
    ("ARROW Shell",  "arrow"),
    ("Services",     "services"),
    ("AI / AURA",    "aura"),
    ("Network/AIM",  "network"),
    ("Events",       "events"),
    ("Storage",      "storage"),
    ("Builder",      "builder"),
    ("Settings",     "settings"),
    ("Help",         "help"),
]


def _init_colors():
    curses.start_color()
    curses.use_default_colors()

    # Define color pairs (foreground, background)
    # -1 = default terminal color
    pairs = [
        (CP_CYAN_BLK,   curses.COLOR_CYAN,    -1),
        (CP_WHITE_BLK,  curses.COLOR_WHITE,   -1),
        (CP_BLK_CYAN,   curses.COLOR_BLACK,   curses.COLOR_CYAN),
        (CP_BLK_BLUE,   curses.COLOR_BLACK,   curses.COLOR_BLUE),
        (CP_GREEN_BLK,  curses.COLOR_GREEN,   -1),
        (CP_RED_BLK,    curses.COLOR_RED,     -1),
        (CP_YELLOW_BLK, curses.COLOR_YELLOW,  -1),
        (CP_BLUE_BLK,   curses.COLOR_BLUE,    -1),
    ]
    for pid, fg, bg in pairs:
        try:
            curses.init_pair(pid, fg, bg)
        except Exception:
            pass


def _safe_addstr(win, y, x, text, attr=0, max_w=None):
    """Draw text, clipping to window width."""
    try:
        h, w = win.getmaxyx()
        if y < 0 or y >= h or x < 0 or x >= w:
            return
        avail = (max_w or w) - x - 1
        if avail <= 0:
            return
        win.addnstr(y, x, str(text)[:avail], avail, attr)
    except curses.error:
        pass


# ── Stats thread ──────────────────────────────────────────────────────────────

class StatsCache:
    def __init__(self):
        self.mem_used    = 0
        self.mem_total   = 1
        self.mem_pct     = 0.0
        self.cpu_pct     = 0.0
        self.svc_run     = 0
        self.svc_total   = 0
        self.online      = False
        self._lock       = threading.Lock()
        self._prev_online = None   # track transitions for event emission

    def update(self, kal):
        try:
            mem = kal.get_memory()
            cpu = kal.get_cpu_percent()
            with self._lock:
                self.mem_used  = mem["used_mb"]
                self.mem_total = mem["total_mb"]
                self.mem_pct   = mem["percent"]
                self.cpu_pct   = cpu
                self.svc_run   = kal.proc_registry.running_count()
                self.svc_total = kal.proc_registry.total_count()
        except Exception:
            pass
        try:
            from aim.aim import get_aim
            now_online  = get_aim().is_online()
            self.online = now_online
            # Emit event on online/offline state transition
            if self._prev_online is not None and self._prev_online != now_online:
                try:
                    from cc.events import get_event_bus, LEVEL_OK, LEVEL_WARN
                    if now_online:
                        get_event_bus().emit("AIM", LEVEL_OK, "Network: connection restored — ONLINE")
                    else:
                        get_event_bus().emit("AIM", LEVEL_WARN, "Network: connection lost — OFFLINE")
                except Exception:
                    pass
            self._prev_online = now_online
        except Exception:
            pass


# ── Command Center ────────────────────────────────────────────────────────────

class CommandCenter:
    def __init__(self):
        from kernel.kal import get_kal
        self.kal         = get_kal()
        self.selected    = 0
        self._stats      = StatsCache()
        self._running    = True
        self._panels     = self._load_panels()
        # Emit startup event
        try:
            from cc.events import get_event_bus, LEVEL_OK
            get_event_bus().emit("CC", LEVEL_OK, "AIOS Command Center started — all systems go")
        except Exception:
            pass

    def _load_panels(self) -> dict:
        panels = {}
        try:
            from cc.panels.home_panel     import HomePanel
            from cc.panels.system_panel   import SystemPanel
            from cc.panels.layers_panel   import LayersPanel
            from cc.panels.services_panel import ServicesPanel
            from cc.panels.aura_panel     import AuraPanel
            from cc.panels.network_panel  import NetworkPanel
            from cc.panels.storage_panel  import StoragePanel
            from cc.panels.builder_panel  import BuilderPanel
            from cc.panels.settings_panel import SettingsPanel
            from cc.panels.help_panel     import HelpPanel
            from cc.panels.events_panel   import EventsPanel

            panels = {
                "home":     HomePanel(),
                "system":   SystemPanel(),
                "layers":   LayersPanel(),
                "services": ServicesPanel(),
                "aura":     AuraPanel(),
                "network":  NetworkPanel(),
                "storage":  StoragePanel(),
                "builder":  BuilderPanel(),
                "settings": SettingsPanel(),
                "help":     HelpPanel(),
                "events":   EventsPanel(),
            }
        except Exception:
            pass
        return panels

    def run(self):
        try:
            curses.wrapper(self._main)
        except Exception:
            pass

    def _main(self, stdscr):
        _init_colors()
        curses.curs_set(0)
        stdscr.keypad(True)
        stdscr.timeout(500)   # 500ms timeout for getch — drives status refresh

        # Start stats background thread
        def _stats_loop():
            while self._running:
                self._stats.update(self.kal)
                time.sleep(2)

        t = threading.Thread(target=_stats_loop, daemon=True)
        t.start()

        while self._running:
            h, w = stdscr.getmaxyx()

            if h < MIN_HEIGHT or w < MIN_WIDTH:
                stdscr.clear()
                msg = f"Terminal too small ({w}x{h}). Need {MIN_WIDTH}x{MIN_HEIGHT}."
                _safe_addstr(stdscr, h // 2, max(0, (w - len(msg)) // 2), msg,
                             curses.color_pair(CP_RED_BLK))
                stdscr.refresh()
                key = stdscr.getch()
                if key == ord("q") or key == ord("Q"):
                    self._running = False
                continue

            stdscr.clear()
            self._draw_layout(stdscr, h, w)
            stdscr.refresh()

            key = stdscr.getch()
            if key == -1:
                continue   # timeout, just redraw (stats update)

            self._handle_key(stdscr, key, h, w)

        self._running = False

    # ── Drawing ───────────────────────────────────────────────────────────────

    def _draw_layout(self, stdscr, h: int, w: int):
        self._draw_header(stdscr, w)
        self._draw_menu(stdscr, h, w)
        self._draw_panel(stdscr, h, w)
        self._draw_status(stdscr, h, w)
        self._draw_borders(stdscr, h, w)

    def _draw_header(self, stdscr, w: int):
        # Top border row
        top = "═" * (w - 2)
        _safe_addstr(stdscr, 0, 0, "╔" + top + "╗",
                     curses.color_pair(CP_CYAN_BLK))

        # Title row
        title  = " ◈  AIOS  AUTONOMOUS INTELLIGENCE OPERATING SYSTEM"
        ver    = "v1.0.0 "
        filler = " " * max(0, w - len(title) - len(ver) - 2)
        _safe_addstr(stdscr, 1, 0, "║",  curses.color_pair(CP_CYAN_BLK))
        _safe_addstr(stdscr, 1, 1, title, curses.color_pair(CP_WHITE_BLK) | curses.A_BOLD)
        _safe_addstr(stdscr, 1, 1 + len(title) + len(filler),
                     ver, curses.color_pair(CP_CYAN_BLK))
        _safe_addstr(stdscr, 1, w - 1, "║", curses.color_pair(CP_CYAN_BLK))

        # Divider with column separator
        div = "╠" + "═" * (MENU_WIDTH - 1) + "╦" + "═" * (w - MENU_WIDTH - 2) + "╣"
        _safe_addstr(stdscr, 2, 0, div, curses.color_pair(CP_CYAN_BLK))

    def _draw_menu(self, stdscr, h: int, w: int):
        content_h = h - HEADER_HEIGHT - STATUS_HEIGHT

        for i, (label, key) in enumerate(MENU_ITEMS):
            row = HEADER_HEIGHT + i
            if row >= h - STATUS_HEIGHT:
                break

            _safe_addstr(stdscr, row, 0, "║", curses.color_pair(CP_CYAN_BLK))

            if i == self.selected:
                indicator = " ► "
                attr = curses.color_pair(CP_BLK_CYAN) | curses.A_BOLD
            else:
                indicator = "   "
                attr = curses.color_pair(CP_WHITE_BLK)

            cell = indicator + label
            padded = cell + " " * max(0, MENU_WIDTH - 2 - len(cell))
            _safe_addstr(stdscr, row, 1, padded, attr)

            _safe_addstr(stdscr, row, MENU_WIDTH - 1, "║",
                         curses.color_pair(CP_CYAN_BLK))

        # Fill empty rows in menu area
        for row in range(HEADER_HEIGHT + len(MENU_ITEMS), h - STATUS_HEIGHT):
            _safe_addstr(stdscr, row, 0, "║", curses.color_pair(CP_CYAN_BLK))
            _safe_addstr(stdscr, row, MENU_WIDTH - 1, "║",
                         curses.color_pair(CP_CYAN_BLK))

    def _draw_panel(self, stdscr, h: int, w: int):
        panel_x = MENU_WIDTH
        panel_w = w - MENU_WIDTH - 1
        panel_y = HEADER_HEIGHT
        panel_h = h - HEADER_HEIGHT - STATUS_HEIGHT

        # Right border for each content row
        for row in range(panel_y, h - STATUS_HEIGHT):
            _safe_addstr(stdscr, row, w - 1, "║", curses.color_pair(CP_CYAN_BLK))

        _, panel_key = MENU_ITEMS[self.selected]

        # ARROW shell: special — we don't draw a panel, we launch the shell
        if panel_key == "arrow":
            self._draw_arrow_prompt(stdscr, panel_y, panel_x, panel_h, panel_w)
            return

        panel = self._panels.get(panel_key)
        if panel:
            try:
                panel.render(stdscr, panel_y, panel_x, panel_h, panel_w,
                             kal=self.kal, curses_mod=curses)
            except Exception as e:
                _safe_addstr(stdscr, panel_y + 1, panel_x + 2, f"Panel error: {e}")

    def _draw_arrow_prompt(self, stdscr, y, x, h, w):
        _safe_addstr(stdscr, y,     x, "  ARROW SHELL", curses.color_pair(CP_CYAN_BLK) | curses.A_BOLD)
        _safe_addstr(stdscr, y + 1, x, "  Autonomous Routing Relay Orchestration Workflow")
        _safe_addstr(stdscr, y + 2, x, "")
        _safe_addstr(stdscr, y + 3, x, "  Press [Enter] to launch ARROW shell.")
        _safe_addstr(stdscr, y + 4, x, "  Type 'cc' inside ARROW to return here.")
        _safe_addstr(stdscr, y + 6, x, "  Capabilities:", curses.A_BOLD)
        _safe_addstr(stdscr, y + 7, x, "    ◈ Full AIOS command set")
        _safe_addstr(stdscr, y + 8, x, "    ◈ All Linux/Termux system commands")
        _safe_addstr(stdscr, y + 9, x, "    ◈ Pipes, redirects, background jobs")
        _safe_addstr(stdscr, y + 10, x, "    ◈ Tab completion + history")
        _safe_addstr(stdscr, y + 11, x, "    ◈ arrow build service|plugin|layer <name>")

    def _draw_status(self, stdscr, h: int, w: int):
        status_row = h - STATUS_HEIGHT

        # Divider
        div = "╠" + "═" * (w - 2) + "╣"
        _safe_addstr(stdscr, status_row, 0, div, curses.color_pair(CP_CYAN_BLK))

        # Status bar content
        s = self._stats
        mem_color = (curses.color_pair(CP_RED_BLK) if s.mem_pct > 80
                     else curses.color_pair(CP_YELLOW_BLK) if s.mem_pct > 60
                     else curses.color_pair(CP_GREEN_BLK))
        cpu_color = (curses.color_pair(CP_RED_BLK) if s.cpu_pct > 80
                     else curses.color_pair(CP_YELLOW_BLK) if s.cpu_pct > 60
                     else curses.color_pair(CP_GREEN_BLK))

        net_str = "◉ ONLINE" if s.online else "○ OFFLINE"
        net_color = curses.color_pair(CP_GREEN_BLK) if s.online else curses.color_pair(CP_RED_BLK)

        svc_str = f"{s.svc_run}/{s.svc_total}"
        ts      = time.strftime("%H:%M:%S")

        health_str = "● HEALTHY"
        health_color = curses.color_pair(CP_GREEN_BLK)
        if s.mem_pct > 90 or s.cpu_pct > 90:
            health_str  = "● CRITICAL"
            health_color = curses.color_pair(CP_RED_BLK)
        elif s.mem_pct > 70 or s.cpu_pct > 70:
            health_str  = "◑ STRESSED"
            health_color = curses.color_pair(CP_YELLOW_BLK)

        # Event count badge
        try:
            from cc.events import get_event_bus
            ev_count = get_event_bus().count()
            ev_str = f"EVT:{ev_count}"
        except Exception:
            ev_str = ""

        bar_row = h - 1
        col = 1
        _safe_addstr(stdscr, bar_row, 0, "║", curses.color_pair(CP_CYAN_BLK))

        def write(text, attr):
            nonlocal col
            _safe_addstr(stdscr, bar_row, col, text, attr)
            col += len(text)

        write(f"  RAM: ", curses.color_pair(CP_WHITE_BLK))
        write(f"{s.mem_used}/{s.mem_total}MB ({s.mem_pct:.0f}%)", mem_color)
        write("  │  CPU: ", curses.color_pair(CP_WHITE_BLK))
        write(f"{s.cpu_pct:.0f}%", cpu_color)
        write("  │  SVC: ", curses.color_pair(CP_WHITE_BLK))
        write(svc_str, curses.color_pair(CP_CYAN_BLK))
        write("  │  ", curses.color_pair(CP_WHITE_BLK))
        write(net_str, net_color)
        write("  │  ", curses.color_pair(CP_WHITE_BLK))
        write(ts, curses.color_pair(CP_CYAN_BLK))
        if ev_str:
            write("  │  ", curses.color_pair(CP_WHITE_BLK))
            write(ev_str, curses.color_pair(CP_CYAN_BLK))
        write("  │  ", curses.color_pair(CP_WHITE_BLK))
        write(health_str, health_color)
        write("  │  Q:quit", curses.color_pair(CP_WHITE_BLK) | curses.A_DIM)

        _safe_addstr(stdscr, bar_row, w - 1, "║", curses.color_pair(CP_CYAN_BLK))

    def _draw_borders(self, stdscr, h: int, w: int):
        # Bottom border
        bot = "╚" + "═" * (w - 2) + "╝"
        _safe_addstr(stdscr, h - 1, 0, bot, curses.color_pair(CP_CYAN_BLK))

    # ── Key handling ──────────────────────────────────────────────────────────

    def _handle_key(self, stdscr, key: int, h: int, w: int):
        if key in (ord("q"), ord("Q")):
            self._running = False

        elif key == curses.KEY_UP:
            self.selected = (self.selected - 1) % len(MENU_ITEMS)

        elif key == curses.KEY_DOWN:
            self.selected = (self.selected + 1) % len(MENU_ITEMS)

        elif key in (curses.KEY_ENTER, 10, 13):
            _, panel_key = MENU_ITEMS[self.selected]
            if panel_key == "arrow":
                self._launch_arrow(stdscr)
            elif panel_key == "aura":
                # Forward key events to AURA panel when active
                pass  # handled in main loop for active panel

        elif key in (ord("1"), ord("2"), ord("3"), ord("4"),
                     ord("5"), ord("6"), ord("7"), ord("8"), ord("9")):
            idx = key - ord("1")
            if idx < len(MENU_ITEMS):
                self.selected = idx

        else:
            # Forward to active panel if it accepts key input
            _, panel_key = MENU_ITEMS[self.selected]
            panel = self._panels.get(panel_key)
            if panel and hasattr(panel, "handle_key"):
                panel.handle_key(key, curses_mod=curses)

    def _launch_arrow(self, stdscr):
        """Suspend curses, launch ARROW shell, resume curses."""
        try:
            from cc.events import get_event_bus, LEVEL_INFO
            get_event_bus().emit("CC", LEVEL_INFO, "Launched ARROW shell")
        except Exception:
            pass
        curses.endwin()
        try:
            from shell.arrow import Arrow
            shell = Arrow()
            shell.run()
        except Exception as e:
            print(f"\n\033[1;31mARROW launch error: {e}\033[0m")
            input("Press Enter to return to Command Center...")
        finally:
            # Emit return event
            try:
                from cc.events import get_event_bus, LEVEL_INFO
                get_event_bus().emit("CC", LEVEL_INFO, "Returned to Command Center from ARROW")
            except Exception:
                pass
            # Reinitialize curses
            stdscr.refresh()
            curses.doupdate()
