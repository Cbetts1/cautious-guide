"""
AIOS Plugin: filebrowser
Curses-based interactive file browser.
Navigate directories, view file sizes, open files with 'cat'.
Keys: ↑/↓ navigate  Enter open/cd  Backspace parent  Q quit  V view file
"""

import os
import sys
import curses

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

PLUGIN_NAME    = "filebrowser"
PLUGIN_VERSION = "1.0.0"


def _human(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.0f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


def _list_dir(path: str) -> list:
    """Return sorted list of (name, is_dir, size) for path."""
    entries = []
    try:
        for name in sorted(os.listdir(path), key=lambda n: (not os.path.isdir(
                os.path.join(path, n)), n.lower())):
            full = os.path.join(path, name)
            is_dir = os.path.isdir(full)
            try:
                size = os.path.getsize(full) if not is_dir else 0
            except OSError:
                size = 0
            entries.append((name, is_dir, size))
    except PermissionError:
        entries = [("<permission denied>", False, 0)]
    return entries


def _filebrowser_main(stdscr, start_path: str):
    curses.curs_set(0)
    stdscr.keypad(True)

    try:
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN,  -1)
        curses.init_pair(2, curses.COLOR_WHITE, -1)
        curses.init_pair(3, curses.COLOR_GREEN, -1)
        curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(5, curses.COLOR_YELLOW, -1)
    except Exception:
        pass

    cwd   = os.path.abspath(start_path)
    sel   = 0
    scroll = 0
    msg   = ""

    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        entries = _list_dir(cwd)
        n = len(entries)

        # Header
        try:
            stdscr.addnstr(0, 0, f" AIOS FileBrowser  {cwd} ", w - 1,
                           curses.color_pair(4) | curses.A_BOLD)
        except curses.error:
            pass

        content_h = h - 3
        if sel >= n:
            sel = max(0, n - 1)
        if sel < scroll:
            scroll = sel
        if sel >= scroll + content_h:
            scroll = sel - content_h + 1

        for i, (name, is_dir, size) in enumerate(entries[scroll: scroll + content_h]):
            row   = i + 1
            abs_i = i + scroll
            is_selected = abs_i == sel
            icon  = "📁 " if is_dir else "   "
            size_str = "<DIR>" if is_dir else _human(size)
            line = f" {icon}{name:<{max(1,w-20)}}{size_str:>8} "
            attr = curses.color_pair(4) | curses.A_BOLD if is_selected else (
                   curses.color_pair(1) if is_dir else curses.color_pair(2))
            try:
                stdscr.addnstr(row, 0, line, w - 1, attr)
            except curses.error:
                pass

        # Status bar
        hint = " ↑↓ navigate  Enter open  Backspace up  V view  Q quit"
        try:
            stdscr.addnstr(h - 2, 0, hint[:w - 1], w - 1, curses.color_pair(5))
        except curses.error:
            pass
        if msg:
            try:
                stdscr.addnstr(h - 1, 0, msg[:w - 1], w - 1, curses.color_pair(3))
            except curses.error:
                pass

        stdscr.refresh()
        key = stdscr.getch()

        if key in (ord("q"), ord("Q")):
            break
        elif key == curses.KEY_UP:
            sel = max(0, sel - 1)
            msg = ""
        elif key == curses.KEY_DOWN:
            sel = min(n - 1, sel + 1)
            msg = ""
        elif key in (curses.KEY_ENTER, 10, 13):
            if n == 0:
                continue
            name, is_dir, _ = entries[sel]
            target = os.path.join(cwd, name)
            if is_dir:
                cwd = target
                sel = 0
                scroll = 0
                msg = ""
            else:
                # View file: exit curses, cat, re-enter
                curses.endwin()
                try:
                    with open(target) as fh:
                        content = fh.read(4096)
                    print(f"\n--- {target} ---\n{content}")
                    if len(content) >= 4096:
                        print("... (truncated at 4096 bytes)")
                    input("\nPress Enter to return...")
                except Exception as e:
                    print(f"Cannot open file: {e}")
                    input("Press Enter to return...")
                stdscr.refresh()
        elif key in (curses.KEY_BACKSPACE, 127, 263):
            parent = os.path.dirname(cwd)
            if parent != cwd:
                cwd = parent
                sel = 0
                scroll = 0
                msg = ""
        elif key in (ord("v"), ord("V")):
            if n > 0:
                name, is_dir, _ = entries[sel]
                target = os.path.join(cwd, name)
                if not is_dir:
                    curses.endwin()
                    try:
                        with open(target) as fh:
                            content = fh.read(4096)
                        print(f"\n--- {target} ---\n{content}")
                        if len(content) >= 4096:
                            print("... (truncated at 4096 bytes)")
                        input("\nPress Enter to return...")
                    except Exception as e:
                        print(f"Cannot open file: {e}")
                        input("Press Enter to return...")
                    stdscr.refresh()
                else:
                    msg = "Press Enter to open directory"


def run(args=None):
    args = args or []
    start_path = args[0] if args else ROOT
    start_path = os.path.expanduser(start_path)
    if not os.path.isdir(start_path):
        print(f"[{PLUGIN_NAME}] Not a directory: {start_path}")
        return
    try:
        from cc.events import get_event_bus, LEVEL_INFO
        get_event_bus().emit(PLUGIN_NAME, LEVEL_INFO, f"FileBrowser opened at {start_path}")
    except Exception:
        pass
    curses.wrapper(_filebrowser_main, start_path)


def status():
    print(f"[{PLUGIN_NAME}] v{PLUGIN_VERSION} — interactive curses file browser")


def help_cmd():
    print(f"""
  [{PLUGIN_NAME}] v{PLUGIN_VERSION} — File Browser
  Commands:
    run [path]   Open browser at path (default: AIOS root)
    status       Show plugin info
    help         This message
  Keys inside browser:
    ↑ / ↓        Navigate
    Enter        Open directory / view file (first 4KB)
    Backspace    Go to parent directory
    V            View selected file
    Q            Quit file browser
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
