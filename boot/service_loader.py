"""
AIOS Service Autostart Engine
Reads config/aios.cfg services.autostart list and starts matching plugins
in background threads at boot time. Each started service is registered
with the KAL ProcessRegistry.
"""

import os
import sys
import json
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG_PATH = os.path.join(ROOT, "config", "aios.cfg")


def _load_autostart() -> list:
    try:
        with open(CFG_PATH) as f:
            cfg = json.load(f)
        return cfg.get("services", {}).get("autostart", [])
    except Exception:
        return []


def autostart_services() -> list:
    """
    Start all plugins listed in config.services.autostart.
    Returns list of names that were successfully started.
    """
    names = _load_autostart()
    if not names:
        return []

    try:
        from plugins.plugin_manager import get_plugin_manager
        from kernel.kal import get_kal
    except Exception:
        return []

    pm  = get_plugin_manager()
    kal = get_kal()
    started = []

    for name in names:
        try:
            plug_dir = os.path.join(ROOT, "plugins", "installed", name)
            if not os.path.isdir(plug_dir):
                # Auto-install if available in registry
                ok, _ = pm.install(name)
                if not ok:
                    continue

            # Try to import and run the plugin's start() if it exposes one
            entry = os.path.join(plug_dir, "main.py")
            if not os.path.isfile(entry):
                continue

            # Run in a daemon thread
            def _run(n=name, e=entry):
                try:
                    import importlib.util
                    spec = importlib.util.spec_from_file_location(f"plugin_{n}", e)
                    mod  = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    if hasattr(mod, "start"):
                        mod.start()
                    elif hasattr(mod, "main"):
                        mod.main(["start"])
                except Exception:
                    pass

            t = threading.Thread(target=_run, daemon=True, name=f"svc-{name}")
            t.start()
            # Register with KAL using the thread's fake pid
            kal.register_process(name, 0, f"autostart plugin: {name}")
            started.append(name)

            try:
                from cc.events import get_event_bus, LEVEL_OK
                get_event_bus().emit("service_loader", LEVEL_OK,
                                     f"Autostarted service: {name}")
            except Exception:
                pass

        except Exception:
            pass

    return started
