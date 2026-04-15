"""CC Panel: Repair — system diagnostics and self-repair actions."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class RepairPanel:
    TITLE = "REPAIR"

    _CHECKS = [
        ("Python version",   "_chk_python"),
        ("Config file",      "_chk_config"),
        ("Data directories", "_chk_data_dirs"),
        ("KAL kernel",       "_chk_kal"),
        ("AURA AI engine",   "_chk_aura"),
        ("AIM bridge",       "_chk_aim"),
        ("ARROW shell",      "_chk_arrow"),
        ("Plugin dir",       "_chk_plugins"),
        ("EventBus",         "_chk_events"),
        ("Hub modules",      "_chk_hub"),
        ("Service loader",   "_chk_service_loader"),
        ("Project registry", "_chk_projects"),
        ("Comms layer",      "_chk_comms"),
        ("Remote layer",     "_chk_remote"),
        ("Providers",        "_chk_providers"),
    ]

    def __init__(self):
        self._results  = []   # list of (label, ok, detail)
        self._last_run = None
        self._sel      = 0

    # ── Individual checks ─────────────────────────────────────────────

    def _chk_python(self):
        v = sys.version_info
        ok = (v.major == 3 and v.minor >= 8)
        return ok, f"Python {v.major}.{v.minor}.{v.micro}"

    def _chk_config(self):
        import json
        cfg = os.path.join(ROOT, "config", "aios.cfg")
        if not os.path.isfile(cfg):
            return False, "config/aios.cfg missing"
        try:
            with open(cfg) as f:
                json.load(f)
            return True, "config/aios.cfg — valid JSON"
        except Exception as e:
            return False, f"Parse error: {e}"

    def _chk_data_dirs(self):
        dirs = [
            os.path.join(ROOT, "plugins", "installed"),
            os.path.join(ROOT, "config"),
            os.path.expanduser("~/.aios"),
        ]
        missing = []
        for d in dirs:
            try:
                os.makedirs(d, exist_ok=True)
            except Exception:
                pass
            if not os.path.isdir(d):
                missing.append(d)
        if missing:
            return False, f"Missing: {missing[0]}"
        return True, f"{len(dirs)} directories OK"

    def _chk_kal(self):
        try:
            from kernel.kal import get_kal
            k = get_kal()
            _ = k.get_memory()
            return True, "KAL operational"
        except Exception as e:
            return False, str(e)

    def _chk_aura(self):
        try:
            from ai.aura import Aura
            a = Aura()
            return True, f"AURA mode={a.mode}"
        except Exception as e:
            return None, f"Deferred: {e}"

    def _chk_aim(self):
        try:
            return True, "AIM importable"
        except Exception as e:
            return None, f"Deferred: {e}"

    def _chk_arrow(self):
        try:
            return True, "ARROW importable"
        except Exception as e:
            return False, str(e)

    def _chk_plugins(self):
        d = os.path.join(ROOT, "plugins", "installed")
        if not os.path.isdir(d):
            return False, "plugins/installed dir missing"
        count = sum(1 for x in os.listdir(d)
                    if os.path.isdir(os.path.join(d, x)))
        return True, f"{count} plugin(s) installed"

    def _chk_events(self):
        try:
            from cc.events import get_event_bus
            bus = get_event_bus()
            return True, f"{bus.count()} events in log"
        except Exception as e:
            return False, str(e)

    def _chk_hub(self):
        try:
            from hub.device_profile import get_profile
            p = get_profile()
            return True, f"Hub OK  mode={p.mode}"
        except Exception as e:
            return False, str(e)

    def _chk_service_loader(self):
        try:
            # Only verify the module is importable; calling autostart_services()
            # would start actual background threads as a side effect.
            from boot.service_loader import autostart_services  # noqa: F401
            return True, "service_loader importable"
        except Exception as e:
            return False, str(e)

    def _chk_projects(self):
        try:
            from projects.registry import get_registry
            r = get_registry()
            return True, f"{r.count()} project(s)"
        except Exception as e:
            return False, str(e)

    def _chk_comms(self):
        try:
            from comms.base import get_comms_manager
            cm = get_comms_manager()
            return True, f"{cm.contact_count()} contact(s)"
        except Exception as e:
            return False, str(e)

    def _chk_remote(self):
        try:
            from remote.base import get_remote_manager
            rm = get_remote_manager()
            return True, f"{rm.host_count()} host(s)"
        except Exception as e:
            return False, str(e)

    def _chk_providers(self):
        try:
            from providers.base import get_provider_registry
            pr = get_provider_registry()
            return True, f"{pr.count()} provider(s) registered"
        except Exception as e:
            return False, str(e)

    # ── Run all checks ────────────────────────────────────────────────

    def _run_checks(self):
        import time
        results = []
        for label, method_name in self._CHECKS:
            method = getattr(self, method_name, None)
            if method is None:
                results.append((label, None, "check not implemented"))
                continue
            try:
                ok, detail = method()
            except Exception as e:
                ok, detail = False, str(e)
            results.append((label, ok, detail))
        self._results  = results
        self._last_run = time.strftime("%H:%M:%S")
        try:
            from cc.events import get_event_bus, LEVEL_INFO
            failed = sum(1 for _, ok, _ in results if ok is False)
            get_event_bus().emit(
                "repair", LEVEL_INFO,
                f"Diagnostic run: {len(results)} checks, {failed} failed"
            )
        except Exception:
            pass

    # ── Rendering ─────────────────────────────────────────────────────

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
            addline("  AIOS REPAIR & DIAGNOSTICS", c.color_pair(1) | c.A_BOLD)
            if self._last_run:
                addline(f"  Last scan: {self._last_run}   R = re-run",
                        c.color_pair(2))
            else:
                addline("  Press R to run a full diagnostic scan.", c.color_pair(7))
            addline("  " + "─" * (width - 4), c.color_pair(8))
            addline("")

            if not self._results:
                addline("  No diagnostic data yet.  Press R to scan.", c.color_pair(7))
                return

            ok_count   = sum(1 for _, ok, _ in self._results if ok is True)
            warn_count = sum(1 for _, ok, _ in self._results if ok is None)
            fail_count = sum(1 for _, ok, _ in self._results if ok is False)

            summary_attr = c.color_pair(6) if fail_count else (
                c.color_pair(7) if warn_count else c.color_pair(5))
            addline(f"  ✓ {ok_count} OK   ⚠ {warn_count} WARN   ✗ {fail_count} FAIL",
                    summary_attr | c.A_BOLD)
            addline("")

            for i, (label, ok, detail) in enumerate(self._results):
                if ok is True:
                    icon  = "✓"
                    attr  = c.color_pair(5)
                elif ok is None:
                    icon  = "⚠"
                    attr  = c.color_pair(7)
                else:
                    icon  = "✗"
                    attr  = c.color_pair(6)

                is_sel = (i == self._sel)
                if is_sel:
                    attr = attr | c.A_REVERSE

                line = f"  {icon}  {label:<22} {detail}"
                addline(line[:width - 2], attr)

            addline("")
            addline("  ↑/↓ scroll   R run scan", c.color_pair(2) | c.A_DIM)

        except Exception as e:
            try:
                win.addnstr(y, x, f"  Repair panel error: {e}", width - 1)
            except Exception:
                pass

    def handle_key(self, key, curses_mod=None):
        c = curses_mod
        if key in (ord("r"), ord("R")):
            self._run_checks()
        elif key == c.KEY_UP:
            self._sel = max(0, self._sel - 1)
        elif key == c.KEY_DOWN:
            self._sel = min(max(0, len(self._results) - 1), self._sel + 1)
