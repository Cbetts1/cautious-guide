"""
AIOS ARROW Shell — Build Commands
arrow build service <name>  — scaffold a new AIOS service
arrow build plugin  <name>  — scaffold a new plugin
arrow build layer   <name>  — scaffold a new system layer
"""

import os
import sys
import json
import time

ROOT   = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from utils.ansi import RESET, BOLD, CYAN, GREEN, RED, YELLOW, WHITE, GRAY


def cmd_arrow_build(args: list) -> int:
    """arrow build <type> <name> [--desc 'description']"""
    if len(args) < 2:
        _build_help()
        return 0

    build_type = args[0].lower()
    name       = args[1].lower().replace(" ", "_")
    desc       = ""

    # Parse optional --desc
    if "--desc" in args:
        idx = args.index("--desc")
        if idx + 1 < len(args):
            desc = args[idx + 1]

    if build_type == "service":
        return _build_service(name, desc)
    elif build_type == "plugin":
        return _build_plugin(name, desc)
    elif build_type == "layer":
        return _build_layer(name, desc)
    else:
        print(f"  {RED}Unknown build type: '{build_type}'. Use: service | plugin | layer{RESET}")
        return 1


def _build_service(name: str, desc: str = "") -> int:
    """Scaffold a new AIOS service under services/<name>/"""
    svc_root = os.path.join(ROOT, "services")
    os.makedirs(svc_root, exist_ok=True)
    svc_dir = os.path.join(svc_root, name)

    if os.path.exists(svc_dir):
        print(f"  {YELLOW}Service '{name}' already exists at {svc_dir}{RESET}")
        return 1

    os.makedirs(svc_dir)

    # ── service.json manifest
    manifest = {
        "name":         name,
        "version":      "1.0.0",
        "description":  desc or f"AIOS service: {name}",
        "type":         "service",
        "entry":        "service.py",
        "autostart":    False,
        "created_at":   time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(os.path.join(svc_dir, "service.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    # ── service.py main file
    code = f'''"""
AIOS Service: {name}
{desc or "Auto-generated service. Replace this implementation."}

Lifecycle:
  start()  — called when service starts
  stop()   — called when service stops
  status() — returns current status dict
"""

import threading
import time


SERVICE_NAME    = "{name}"
SERVICE_VERSION = "1.0.0"


class {_to_class(name)}Service:
    def __init__(self):
        self._running = False
        self._thread  = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name=f"svc-{name}"
        )
        self._thread.start()
        print(f"[{{SERVICE_NAME}}] Service started.")

    def stop(self):
        self._running = False
        print(f"[{{SERVICE_NAME}}] Service stopped.")

    def _run_loop(self):
        """Main service loop. Replace with real logic."""
        while self._running:
            # TODO: implement service logic here
            time.sleep(5)

    def status(self) -> dict:
        return {{
            "name":    SERVICE_NAME,
            "version": SERVICE_VERSION,
            "running": self._running,
        }}


# ── Entry point ──────────────────────────────────────────────────────────────
_instance = None

def get_service():
    global _instance
    if _instance is None:
        _instance = {_to_class(name)}Service()
    return _instance

if __name__ == "__main__":
    import sys
    svc = get_service()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "start"
    if cmd == "start":
        svc.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            svc.stop()
    elif cmd == "stop":
        svc.stop()
    elif cmd == "status":
        import json
        print(json.dumps(svc.status(), indent=2))
'''

    with open(os.path.join(svc_dir, "service.py"), "w") as f:
        f.write(code)

    # ── README
    with open(os.path.join(svc_dir, "README.md"), "w") as f:
        f.write(f"# AIOS Service: {name}\n\n{desc or 'Auto-generated service.'}\n\n"
                f"## Usage\n\n```bash\npython3 service.py start\npython3 service.py stop\n"
                f"python3 service.py status\n```\n")

    _print_success("service", name, svc_dir, [
        "service.json  — service manifest",
        "service.py    — main service implementation",
        "README.md     — documentation",
    ])
    return 0


def _build_plugin(name: str, desc: str = "") -> int:
    """Scaffold a new plugin under plugins/installed/<name>/"""
    plug_dir = os.path.join(ROOT, "plugins", "installed", name)

    if os.path.exists(plug_dir):
        print(f"  {YELLOW}Plugin '{name}' already exists.{RESET}")
        return 1

    os.makedirs(plug_dir)

    manifest = {
        "name":         name,
        "version":      "1.0.0",
        "description":  desc or f"AIOS plugin: {name}",
        "type":         "tool",
        "entry":        "main.py",
        "commands":     ["run", "status"],
        "requires":     [],
        "installed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "enabled":      True,
    }
    with open(os.path.join(plug_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    code = f'''"""
AIOS Plugin: {name}
{desc or "Auto-generated plugin. Replace this implementation."}
"""
import sys


PLUGIN_NAME    = "{name}"
PLUGIN_VERSION = "1.0.0"


def run(args=None):
    """Main plugin action. Replace with real logic."""
    print(f"[{{PLUGIN_NAME}}] Running with args: {{args}}")


def status():
    print(f"[{{PLUGIN_NAME}}] v{{PLUGIN_VERSION}} — active")


def main(args=None):
    args = args or []
    cmd = args[0] if args else "run"
    if cmd == "run":
        run(args[1:])
    elif cmd == "status":
        status()
    else:
        print(f"[{{PLUGIN_NAME}}] Unknown command: {{cmd}}")


if __name__ == "__main__":
    main(sys.argv[1:])
'''
    with open(os.path.join(plug_dir, "main.py"), "w") as f:
        f.write(code)

    _print_success("plugin", name, plug_dir, [
        "manifest.json  — plugin manifest (type/commands/requires)",
        "main.py        — plugin implementation",
    ])
    print(f"  {CYAN}The plugin is now installed and visible via 'aios list installed'.{RESET}\n")
    return 0


def _build_layer(name: str, desc: str = "") -> int:
    """Scaffold a new system layer (top-level module)."""
    layer_dir = os.path.join(ROOT, name)

    if os.path.exists(layer_dir):
        print(f"  {YELLOW}Layer '{name}' already exists at {layer_dir}{RESET}")
        return 1

    os.makedirs(layer_dir)

    init_code = f'"""AIOS Layer: {name}\n{desc or ""}\n"""\n'
    with open(os.path.join(layer_dir, "__init__.py"), "w") as f:
        f.write(init_code)

    main_code = f'''"""
AIOS Layer: {name}
{desc or "Auto-generated system layer. Replace this implementation."}

Layers are top-level AIOS subsystems. They hook into the KAL
and register with the Command Center via the panel system.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from kernel.kal import get_kal


LAYER_NAME    = "{name}"
LAYER_VERSION = "1.0.0"


class {_to_class(name)}Layer:
    def __init__(self):
        self.kal = get_kal()

    def initialize(self) -> bool:
        """Called by AIOS during boot. Return True on success."""
        print(f"[{name}] Layer initialized.")
        return True

    def get_status(self) -> dict:
        return {{
            "name":    LAYER_NAME,
            "version": LAYER_VERSION,
            "active":  True,
        }}


_instance = None

def get_layer():
    global _instance
    if _instance is None:
        _instance = {_to_class(name)}Layer()
    return _instance
'''
    with open(os.path.join(layer_dir, f"{name}.py"), "w") as f:
        f.write(main_code)

    layer_manifest = {
        "name":       name,
        "version":    "1.0.0",
        "description": desc or f"AIOS layer: {name}",
        "type":       "layer",
        "entry":      f"{name}.py",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(os.path.join(layer_dir, "layer.json"), "w") as f:
        json.dump(layer_manifest, f, indent=2)

    _print_success("layer", name, layer_dir, [
        "__init__.py   — package init",
        f"{name}.py    — layer implementation",
        "layer.json    — layer manifest",
    ])
    print(f"  {CYAN}Import with: from {name}.{name} import get_layer{RESET}\n")
    return 0


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_class(name: str) -> str:
    """Convert snake_case to CamelCase."""
    return "".join(word.capitalize() for word in name.split("_"))


def _print_success(build_type: str, name: str, path: str, files: list):
    print(f"\n  {GREEN}✓ Built {build_type}: '{name}'{RESET}")
    print(f"  {CYAN}Location: {path}{RESET}")
    print(f"\n  {BOLD}Files created:{RESET}")
    for f in files:
        print(f"    {CYAN}+{RESET} {f}")


def _build_help():
    print(f"""
  {CYAN}{'─' * 54}{RESET}
  {BOLD}ARROW BUILD SYSTEM{RESET}
  {CYAN}{'─' * 54}{RESET}
  {WHITE}arrow build service <name>{RESET}
      Scaffold a new AIOS background service.
      Creates: services/<name>/service.py + manifest

  {WHITE}arrow build plugin <name>{RESET}
      Scaffold and install a new plugin.
      Creates: plugins/installed/<name>/main.py + manifest

  {WHITE}arrow build layer <name>{RESET}
      Scaffold a new top-level AIOS system layer.
      Creates: <name>/__init__.py + <name>.py + manifest

  {GRAY}Options:{RESET}
    --desc 'description'   Add a description to the manifest
  {CYAN}{'─' * 54}{RESET}
""")
