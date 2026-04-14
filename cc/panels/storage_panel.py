"""CC Panel: Storage."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class StoragePanel:
    TITLE = "STORAGE"

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
            addline("")

            seen = set()
            for path, label in check_paths:
                if not os.path.exists(path):
                    continue
                try:
                    st = os.statvfs(path)
                    dev = (st.f_fsid if hasattr(st, 'f_fsid') else path)
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

            # AIOS directory sizes
            addline("  AIOS DIRECTORIES", c.color_pair(3) | c.A_BOLD)
            subdirs = ["plugins/installed", "config", "ai/rules"]
            for sd in subdirs:
                full = os.path.join(ROOT, sd)
                if os.path.isdir(full):
                    try:
                        total = sum(
                            os.path.getsize(os.path.join(dp, f))
                            for dp, _, files in os.walk(full)
                            for f in files
                        )
                        addline(f"  {sd:<28} {total // 1024}KB")
                    except Exception:
                        pass

        except Exception as e:
            try:
                win.addnstr(y, x, f"  Error: {e}", width - 1)
            except Exception:
                pass
