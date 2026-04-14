"""CC Panel: Builder — scaffold services, plugins, layers."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class BuilderPanel:
    TITLE = "BUILDER"

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
            addline("  ARROW BUILD SYSTEM", c.color_pair(3) | c.A_BOLD)
            addline("  Use ARROW shell to execute build commands.")
            addline("")

            addline("  BUILD TARGETS", c.A_BOLD)
            addline("")
            addline("  arrow build service <name>")
            addline("    Scaffold a new background service.")
            addline("    → services/<name>/service.py + service.json")
            addline("")
            addline("  arrow build plugin <name>")
            addline("    Build + install a new plugin.")
            addline("    → plugins/installed/<name>/main.py + manifest.json")
            addline("")
            addline("  arrow build layer <name>")
            addline("    Create a new top-level AIOS system layer.")
            addline("    → <name>/<name>.py + layer.json")
            addline("")

            # Show existing services
            svc_dir = os.path.join(ROOT, "services")
            if os.path.isdir(svc_dir):
                svcs = [d for d in os.listdir(svc_dir)
                        if os.path.isdir(os.path.join(svc_dir, d))]
                if svcs:
                    addline("  BUILT SERVICES", c.A_BOLD)
                    for s in svcs:
                        addline(f"    ◈ {s}")
                    addline("")

            # Show installed plugins
            plug_dir = os.path.join(ROOT, "plugins", "installed")
            if os.path.isdir(plug_dir):
                plugs = [d for d in os.listdir(plug_dir)
                         if os.path.isdir(os.path.join(plug_dir, d))]
                if plugs:
                    addline("  INSTALLED PLUGINS", c.A_BOLD)
                    for p in plugs:
                        addline(f"    ◈ {p}")

        except Exception as e:
            try:
                win.addnstr(y, x, f"  Error: {e}", width - 1)
            except Exception:
                pass
