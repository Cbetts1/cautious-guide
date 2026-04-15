"""
AIOS Plugin: codepad
Minimal curses text editor.
  Ctrl+S  — save
  Ctrl+Q  — quit (prompts if unsaved changes)
  Ctrl+G  — go to line
  Arrow keys — navigate
  Home / End — line start / end
  PgUp / PgDn — scroll
"""

import os
import sys
import curses

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

PLUGIN_NAME    = "codepad"
PLUGIN_VERSION = "1.0.0"


class Editor:
    def __init__(self, path: str):
        self.path    = path
        self.lines   = [""]
        self.cx      = 0   # cursor x (column)
        self.cy      = 0   # cursor y (row in file)
        self.scroll  = 0   # first visible line
        self.dirty   = False
        self.message = ""
        self._load()

    def _load(self):
        if os.path.isfile(self.path):
            try:
                with open(self.path) as f:
                    content = f.read()
                self.lines = content.split("\n")
                if self.lines and self.lines[-1] == "":
                    self.lines.pop()
                if not self.lines:
                    self.lines = [""]
            except Exception as e:
                self.message = f"Load error: {e}"
        self.dirty = False

    def save(self):
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
            with open(self.path, "w") as f:
                f.write("\n".join(self.lines) + "\n")
            self.dirty   = False
            self.message = f"Saved: {self.path}"
            try:
                from cc.events import get_event_bus, LEVEL_OK
                get_event_bus().emit(PLUGIN_NAME, LEVEL_OK, f"Saved {self.path}")
            except Exception:
                pass
        except Exception as e:
            self.message = f"Save error: {e}"

    def current_line(self) -> str:
        if self.cy < len(self.lines):
            return self.lines[self.cy]
        return ""

    def run(self, stdscr):
        curses.curs_set(1)
        stdscr.keypad(True)
        try:
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_CYAN,  -1)
            curses.init_pair(2, curses.COLOR_WHITE, -1)
            curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_CYAN)
            curses.init_pair(5, curses.COLOR_YELLOW, -1)
            curses.init_pair(6, curses.COLOR_RED,   -1)
        except Exception:
            pass

        while True:
            h, w = stdscr.getmaxyx()
            stdscr.clear()

            # Header
            title = f" CodePad  {self.path}{'*' if self.dirty else ''} "
            try:
                stdscr.addnstr(0, 0, title[:w - 1], w - 1,
                               curses.color_pair(4) | curses.A_BOLD)
            except curses.error:
                pass

            content_h = h - 2
            # Adjust scroll
            if self.cy < self.scroll:
                self.scroll = self.cy
            if self.cy >= self.scroll + content_h:
                self.scroll = self.cy - content_h + 1

            # Draw lines
            for i in range(content_h):
                ln = i + self.scroll
                row = i + 1
                if ln < len(self.lines):
                    num  = f"{ln + 1:4} "
                    text = self.lines[ln]
                    try:
                        stdscr.addnstr(row, 0, num, 5, curses.color_pair(5))
                        stdscr.addnstr(row, 5, text[:w - 6], w - 6, curses.color_pair(2))
                    except curses.error:
                        pass

            # Status bar
            info = (f" L{self.cy + 1}:C{self.cx + 1}  "
                    f"^S save  ^Q quit  ^G goto  | {self.message}")
            try:
                stdscr.addnstr(h - 1, 0, info[:w - 1], w - 1, curses.color_pair(1))
            except curses.error:
                pass

            # Place cursor
            screen_y = self.cy - self.scroll + 1
            screen_x = min(self.cx + 5, w - 1)
            try:
                stdscr.move(screen_y, screen_x)
            except curses.error:
                pass

            stdscr.refresh()
            key = stdscr.getch()
            self.message = ""
            self._handle(key, stdscr, h, w)

    def _handle(self, key, stdscr, h, w):
        # Ctrl+S = 19, Ctrl+Q = 17, Ctrl+G = 7
        if key == 19:      # Ctrl+S
            self.save()
        elif key == 17:    # Ctrl+Q
            if self.dirty:
                self.message = "Unsaved changes! Press Ctrl+Q again to quit."
                self.dirty = False  # next Ctrl+Q will quit
            else:
                raise SystemExit(0)
        elif key == 7:     # Ctrl+G  go to line
            curses.echo()
            try:
                stdscr.addnstr(h - 1, 0, " Go to line: ", 20, curses.color_pair(1))
                s = stdscr.getstr(h - 1, 13, 6).decode("utf-8", errors="replace")
                n = int(s.strip()) - 1
                self.cy = max(0, min(n, len(self.lines) - 1))
                self.cx = 0
            except Exception:
                pass
            finally:
                curses.noecho()
        elif key == curses.KEY_UP:
            self.cy = max(0, self.cy - 1)
            self.cx = min(self.cx, len(self.current_line()))
        elif key == curses.KEY_DOWN:
            self.cy = min(len(self.lines) - 1, self.cy + 1)
            self.cx = min(self.cx, len(self.current_line()))
        elif key == curses.KEY_LEFT:
            if self.cx > 0:
                self.cx -= 1
            elif self.cy > 0:
                self.cy -= 1
                self.cx = len(self.current_line())
        elif key == curses.KEY_RIGHT:
            line = self.current_line()
            if self.cx < len(line):
                self.cx += 1
            elif self.cy < len(self.lines) - 1:
                self.cy += 1
                self.cx = 0
        elif key == curses.KEY_HOME:
            self.cx = 0
        elif key == curses.KEY_END:
            self.cx = len(self.current_line())
        elif key == curses.KEY_PPAGE:
            self.cy = max(0, self.cy - (h - 3))
        elif key == curses.KEY_NPAGE:
            self.cy = min(len(self.lines) - 1, self.cy + (h - 3))
        elif key in (10, 13):  # Enter
            line = self.lines[self.cy]
            self.lines[self.cy] = line[:self.cx]
            self.lines.insert(self.cy + 1, line[self.cx:])
            self.cy += 1
            self.cx  = 0
            self.dirty = True
        elif key in (127, curses.KEY_BACKSPACE, 263):  # Backspace
            if self.cx > 0:
                line = self.lines[self.cy]
                self.lines[self.cy] = line[:self.cx - 1] + line[self.cx:]
                self.cx -= 1
                self.dirty = True
            elif self.cy > 0:
                prev = self.lines[self.cy - 1]
                self.cx = len(prev)
                self.lines[self.cy - 1] = prev + self.lines[self.cy]
                del self.lines[self.cy]
                self.cy -= 1
                self.dirty = True
        elif key == curses.KEY_DC:  # Delete
            line = self.lines[self.cy]
            if self.cx < len(line):
                self.lines[self.cy] = line[:self.cx] + line[self.cx + 1:]
                self.dirty = True
            elif self.cy < len(self.lines) - 1:
                self.lines[self.cy] = line + self.lines[self.cy + 1]
                del self.lines[self.cy + 1]
                self.dirty = True
        elif 32 <= key <= 126:  # Printable
            line = self.lines[self.cy]
            self.lines[self.cy] = line[:self.cx] + chr(key) + line[self.cx:]
            self.cx += 1
            self.dirty = True


def run(args=None):
    args = args or []
    if not args:
        print(f"[{PLUGIN_NAME}] Usage: codepad run <file>")
        return
    path = os.path.expanduser(args[0])
    try:
        from cc.events import get_event_bus, LEVEL_INFO
        get_event_bus().emit(PLUGIN_NAME, LEVEL_INFO, f"Editing {path}")
    except Exception:
        pass
    editor = Editor(path)
    try:
        curses.wrapper(editor.run)
    except SystemExit:
        pass


def status():
    print(f"[{PLUGIN_NAME}] v{PLUGIN_VERSION} — minimal curses text editor")


def help_cmd():
    print(f"""
  [{PLUGIN_NAME}] v{PLUGIN_VERSION} — Code Pad Editor
  Commands:
    run <file>   Open file for editing (creates if not exists)
    status       Show plugin info
    help         This message
  Keys inside editor:
    ↑/↓/←/→     Navigate
    Home / End   Line start / end
    PgUp / PgDn  Scroll
    Ctrl+G       Go to line number
    Ctrl+S       Save
    Ctrl+Q       Quit (confirm if unsaved)
""")


def main(args=None):
    args = args or []
    cmd  = args[0] if args else "help"
    if   cmd == "run":    run(args[1:])
    elif cmd == "status": status()
    elif cmd == "help":   help_cmd()
    else:
        print(f"[{PLUGIN_NAME}] Unknown command '{cmd}'. Try 'help'.")


if __name__ == "__main__":
    main(sys.argv[1:])
