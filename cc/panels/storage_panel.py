"""CC Panel: Storage — disk usage, AIOS dirs, pycache cleanup."""
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class StoragePanel:
    TITLE = "STORAGE"

    def __init__(self):
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

        def bar(pct, bar_w=25):
            filled = int(bar_w * pct / 100)
            color  = "▓" if pct < 70 else ("▓" if pct < 90 else "█")
            return color * filled + "░" * (bar_w - filled)

        try:
            check_paths = [
                ("/",               "Root"),
                (ROOT,              "AIOS"),
                (os.path.expanduser("~"), "Home"),
            ]

            addline("  DISK USAGE", c.color_pair(3) | c.A_BOLD)
            addline("  [C] Clean __pycache__  |  " + (self._msg or "Press C to free cache bytes"))
            addline("")

            seen = set()
            for path, label in check_paths:
                if not os.path.exists(path):
                    continue
                try:
                    st = os.statvfs(path)
                    key = (st.f_blocks, st.f_frsize)
                    if key in seen:
                        continue
                    seen.add(key)
                    total_mb = (st.f_blocks * st.f_frsize) // (1024 * 1024)
                    free_mb  = (st.f_bavail * st.f_frsize) // (1024 * 1024)
                    used_mb  = total_mb - free_mb
                    pct      = (used_mb / total_mb * 100) if total_mb else 0
                    bar_w    = max(15, width - 35)
                    b        = bar(pct, bar_w)
                    addline(f"  {label:<8} [{b}] {pct:.0f}%")
                    addline(f"           {used_mb}MB used / {total_mb}MB total / {free_mb}MB free")
                    addline("")
                except Exception:
                    pass

            # AIOS directory sizes with file counts
            addline("  AIOS DIRECTORIES", c.color_pair(3) | c.A_BOLD)
            aios_dirs = [
                ("plugins/installed", "Installed plugins"),
                ("config",            "Configuration"),
                ("ai/rules",          "AI rules"),
                ("services",          "Built services"),
            ]
            for rel, label in aios_dirs:
                full = os.path.join(ROOT, rel)
                if os.path.isdir(full):
                    try:
                        total_bytes = 0
                        file_count  = 0
                        for dp, _, files in os.walk(full):
                            for fn in files:
                                try:
                                    total_bytes += os.path.getsize(os.path.join(dp, fn))
                                    file_count  += 1
                                except OSError:
                                    pass
                        addline(f"  {rel:<28} {total_bytes // 1024:>6}KB  ({file_count} files)")
                    except Exception:
                        pass

            # ~/.aios data directory
            aios_home = os.path.expanduser("~/.aios")
            if os.path.isdir(aios_home):
                try:
                    total_bytes = sum(
                        os.path.getsize(os.path.join(dp, fn))
                        for dp, _, files in os.walk(aios_home)
                        for fn in files
                    )
                    addline(f"  {'~/.aios':<28} {total_bytes // 1024:>6}KB")
                except Exception:
                    pass

        except Exception as e:
            try:
                win.addnstr(y, x, f"  Error: {e}", width - 1)
            except Exception:
                pass

    def handle_key(self, key, curses_mod=None):
        if key in (ord("c"), ord("C")):
            freed = _clean_pycache(ROOT)
            self._msg = f"Cleaned {freed // 1024}KB of __pycache__"
            try:
                from cc.events import get_event_bus, LEVEL_OK
                get_event_bus().emit("storage", LEVEL_OK,
                                     f"Cleaned __pycache__: freed {freed // 1024}KB")
            except Exception:
                pass


def _clean_pycache(root: str) -> int:
    """Remove all __pycache__ dirs under root. Returns bytes freed."""
    freed = 0
    for dirpath, dirnames, _ in os.walk(root):
        for dn in list(dirnames):
            if dn == "__pycache__":
                full = os.path.join(dirpath, dn)
                try:
                    size = sum(
                        os.path.getsize(os.path.join(dp, fn))
                        for dp, _, files in os.walk(full)
                        for fn in files
                    )
                    shutil.rmtree(full, ignore_errors=True)
                    freed += size
                    dirnames.remove(dn)
                except Exception:
                    pass
    return freed
