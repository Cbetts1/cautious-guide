"""CC Panel: Settings — view and edit AIOS configuration live."""
import os
import json

ROOT     = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CFG_PATH = os.path.join(ROOT, "config", "aios.cfg")

# (section, key, editable)
_FIELDS = [
    ("system",  "name",               True),
    ("system",  "hostname",           True),
    ("boot",    "show_post",          True),
    ("boot",    "post_delay",         True),
    ("boot",    "verbose",            True),
    ("auth",    "pin_required",       True),
    ("auth",    "max_attempts",       True),
    ("cc",      "default_panel",      True),
    ("cc",      "status_refresh_sec", True),
    ("cc",      "theme",              True),
    ("aura",    "mode",               True),
    ("aura",    "model_path",         True),
    ("aura",    "context_size",       True),
    ("aim",     "enabled",            True),
    ("aim",     "bridge_port",        True),
    ("aim",     "proxy_enabled",      True),
    ("shell",   "history_size",       True),
    ("plugins", "auto_update",        True),
]

_SENSITIVE = {"pin_hash", "pin_salt"}


class SettingsPanel:
    TITLE = "SETTINGS"

    def __init__(self):
        self._sel   = 0
        self._msg   = ""
        self._edit  = False
        self._input = ""

    def _load(self) -> dict:
        try:
            with open(CFG_PATH) as f:
                return json.load(f)
        except Exception:
            return {}

    def _save(self, cfg: dict):
        try:
            with open(CFG_PATH, "w") as f:
                json.dump(cfg, f, indent=2)
            self._msg = "Config saved."
            try:
                from cc.events import get_event_bus, LEVEL_OK
                get_event_bus().emit("settings", LEVEL_OK, "Config file saved")
            except Exception:
                pass
        except Exception as e:
            self._msg = f"Save error: {e}"

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
            cfg = self._load()

            addline("  AIOS CONFIGURATION", c.color_pair(3) | c.A_BOLD)
            addline(f"  {CFG_PATH}")
            addline(f"  ↑/↓ navigate  Enter edit  Esc cancel  | {self._msg}")
            addline("  " + "─" * (width - 4))

            if self._sel >= len(_FIELDS):
                self._sel = len(_FIELDS) - 1

            for i, (section, key, editable) in enumerate(_FIELDS):
                if row >= y + height - 1:
                    break
                val = cfg.get(section, {}).get(key, "(not set)")
                if key in _SENSITIVE:
                    val = "***"
                is_sel = (i == self._sel)

                if is_sel and self._edit:
                    display = f"  [{section}] {key:<22} = {self._input}_"
                    attr = c.color_pair(3) | c.A_BOLD
                elif is_sel:
                    display = f"  [{section}] {key:<22} = {val}"
                    attr = c.color_pair(3) | c.A_REVERSE
                else:
                    display = f"  [{section}] {key:<22} = {val}"
                    attr = c.color_pair(2)
                addline(display[:width - 2], attr)

        except Exception as e:
            try:
                win.addnstr(y, x, f"  Error: {e}", width - 1)
            except Exception:
                pass

    def handle_key(self, key, curses_mod=None):
        c = curses_mod
        ESC = 27

        if self._edit:
            if key == 10 or key == 13:       # Enter — commit
                self._commit()
            elif key == ESC:                  # Esc — cancel
                self._edit  = False
                self._input = ""
                self._msg   = "Edit cancelled."
            elif key in (127, c.KEY_BACKSPACE, 263):
                self._input = self._input[:-1]
            elif 32 <= key <= 126:
                self._input += chr(key)
        else:
            if key == c.KEY_UP:
                self._sel = max(0, self._sel - 1)
                self._msg = ""
            elif key == c.KEY_DOWN:
                self._sel = min(len(_FIELDS) - 1, self._sel + 1)
                self._msg = ""
            elif key in (10, 13):            # Enter — start editing
                section, key_name, editable = _FIELDS[self._sel]
                if not editable or key_name in _SENSITIVE:
                    self._msg = f"'{key_name}' is read-only (edit aios.cfg manually)."
                    return
                cfg = self._load()
                self._input = str(cfg.get(section, {}).get(key_name, ""))
                self._edit  = True
                self._msg   = "Editing — Enter to save, Esc to cancel"

    def _commit(self):
        """Write the edited value back to aios.cfg."""
        section, key_name, _ = _FIELDS[self._sel]
        cfg = self._load()
        if section not in cfg:
            cfg[section] = {}
        raw = self._input.strip()
        # Type coercion
        if raw.lower() in ("true", "false"):
            val = raw.lower() == "true"
        else:
            try:
                val = int(raw)
            except ValueError:
                try:
                    val = float(raw)
                except ValueError:
                    val = raw
        cfg[section][key_name] = val
        self._save(cfg)
        self._edit  = False
        self._input = ""
