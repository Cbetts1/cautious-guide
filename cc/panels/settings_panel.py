"""CC Panel: Settings."""
import os
import json

ROOT     = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CFG_PATH = os.path.join(ROOT, "config", "aios.cfg")


class SettingsPanel:
    TITLE = "SETTINGS"

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
            try:
                with open(CFG_PATH) as f:
                    cfg = json.load(f)
            except Exception:
                cfg = {}

            addline("  AIOS CONFIGURATION", c.color_pair(3) | c.A_BOLD)
            addline(f"  Config file: {CFG_PATH}")
            addline("")

            sections = {
                "system":  ["name", "version", "hostname"],
                "boot":    ["show_post", "post_delay", "verbose"],
                "auth":    ["pin_required", "max_attempts"],
                "cc":      ["default_panel", "status_refresh_sec", "theme"],
                "aura":    ["mode", "model_path", "context_size"],
                "aim":     ["enabled", "bridge_port", "proxy_enabled"],
                "plugins": ["auto_update"],
            }

            for section, keys in sections.items():
                sec_data = cfg.get(section, {})
                addline(f"  [{section.upper()}]", c.A_BOLD)
                for key in keys:
                    val = sec_data.get(key, "(not set)")
                    # Mask sensitive fields
                    if key in ("pin_hash", "pin_salt"):
                        val = "***"
                    addline(f"    {key:<22} = {val}")
                addline("")

            addline("  To change settings:", c.A_BOLD)
            addline("  Edit config/aios.cfg directly, then restart AIOS.")
            addline("  To reset PIN: clear pin_hash and pin_salt in config.")

        except Exception as e:
            try:
                win.addnstr(y, x, f"  Error: {e}", width - 1)
            except Exception:
                pass
