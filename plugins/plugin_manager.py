"""
AIOS Plugin Manager
Plugins install/remove like software packages.
Each plugin is a directory under plugins/installed/<name>/
with a manifest.json describing it.
"""

import os
import sys
import json
import shutil
import time

ROOT         = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTALLED    = os.path.join(ROOT, "plugins", "installed")
REGISTRY_PATH = os.path.join(ROOT, "plugins", "registry.json")

MANIFEST_TEMPLATE = {
    "name":        "",
    "version":     "1.0.0",
    "description": "",
    "type":        "tool",         # "service" | "tool" | "bridge"
    "entry":       "main.py",
    "commands":    [],
    "requires":    [],
    "installed_at": "",
    "enabled":     True,
}


class Plugin:
    def __init__(self, path: str):
        self.path = path
        self.manifest = self._load_manifest()
        self.name     = self.manifest.get("name", os.path.basename(path))

    def _load_manifest(self) -> dict:
        mf = os.path.join(self.path, "manifest.json")
        try:
            with open(mf) as f:
                return json.load(f)
        except Exception:
            return dict(MANIFEST_TEMPLATE)

    def is_enabled(self) -> bool:
        return self.manifest.get("enabled", True)

    def get_entry(self) -> str:
        return os.path.join(self.path, self.manifest.get("entry", "main.py"))

    def to_dict(self) -> dict:
        return {
            "name":        self.name,
            "version":     self.manifest.get("version", "?"),
            "description": self.manifest.get("description", ""),
            "type":        self.manifest.get("type", "tool"),
            "enabled":     self.is_enabled(),
            "path":        self.path,
        }


class PluginManager:
    def __init__(self):
        os.makedirs(INSTALLED, exist_ok=True)
        self._plugins: dict[str, Plugin] = {}
        self._load_installed()

    # ── Internal ──────────────────────────────────────────────────────

    def _load_installed(self):
        self._plugins = {}
        if not os.path.isdir(INSTALLED):
            return
        for name in os.listdir(INSTALLED):
            plug_path = os.path.join(INSTALLED, name)
            if os.path.isdir(plug_path):
                p = Plugin(plug_path)
                self._plugins[p.name] = p

    def _load_registry(self) -> list:
        try:
            with open(REGISTRY_PATH) as f:
                data = json.load(f)
            return data.get("available", [])
        except Exception:
            return []

    # ── Public API ────────────────────────────────────────────────────

    def list_installed(self) -> list:
        """Return list of installed plugin dicts."""
        return [p.to_dict() for p in self._plugins.values()]

    def list_available(self) -> list:
        """Return list of available plugins from registry."""
        registry = self._load_registry()
        installed_names = set(self._plugins.keys())
        for item in registry:
            item["installed"] = item["name"] in installed_names
        return registry

    def is_installed(self, name: str) -> bool:
        return name in self._plugins

    def install(self, name: str) -> tuple[bool, str]:
        """
        Install a plugin by name.
        For bundled plugins: creates the directory and manifest.
        Returns (ok, message).
        """
        if name in self._plugins:
            return False, f"Plugin '{name}' is already installed."

        registry = self._load_registry()
        spec = next((r for r in registry if r["name"] == name), None)
        if spec is None:
            return False, f"Plugin '{name}' not found in registry. Use 'aios list plugins' to see available."

        plug_path = os.path.join(INSTALLED, name)
        try:
            os.makedirs(plug_path, exist_ok=True)

            # Write manifest
            manifest = dict(MANIFEST_TEMPLATE)
            manifest.update({
                "name":         spec["name"],
                "version":      spec.get("version", "1.0.0"),
                "description":  spec.get("description", ""),
                "type":         spec.get("type", "tool"),
                "requires":     spec.get("requires", []),
                "installed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            })
            with open(os.path.join(plug_path, "manifest.json"), "w") as f:
                json.dump(manifest, f, indent=2)

            # Write stub main.py
            entry_code = _generate_stub(spec)
            with open(os.path.join(plug_path, "main.py"), "w") as f:
                f.write(entry_code)

            # Reload
            self._load_installed()
            return True, f"Plugin '{name}' installed successfully at {plug_path}"

        except Exception as e:
            # Clean up on failure
            shutil.rmtree(plug_path, ignore_errors=True)
            return False, f"Install failed: {e}"

    def remove(self, name: str) -> tuple[bool, str]:
        """Uninstall a plugin. Removes its directory."""
        if name not in self._plugins:
            return False, f"Plugin '{name}' is not installed."

        plug_path = os.path.join(INSTALLED, name)
        try:
            shutil.rmtree(plug_path)
            self._load_installed()
            return True, f"Plugin '{name}' removed."
        except Exception as e:
            return False, f"Remove failed: {e}"

    def enable(self, name: str) -> tuple[bool, str]:
        if name not in self._plugins:
            return False, f"Plugin '{name}' not found."
        p = self._plugins[name]
        p.manifest["enabled"] = True
        mf_path = os.path.join(p.path, "manifest.json")
        with open(mf_path, "w") as f:
            json.dump(p.manifest, f, indent=2)
        return True, f"Plugin '{name}' enabled."

    def disable(self, name: str) -> tuple[bool, str]:
        if name not in self._plugins:
            return False, f"Plugin '{name}' not found."
        p = self._plugins[name]
        p.manifest["enabled"] = False
        mf_path = os.path.join(p.path, "manifest.json")
        with open(mf_path, "w") as f:
            json.dump(p.manifest, f, indent=2)
        return True, f"Plugin '{name}' disabled."

    def run_plugin(self, name: str, args: list = None) -> tuple[bool, str]:
        """Run a plugin's main entry point."""
        if name not in self._plugins:
            return False, f"Plugin '{name}' not installed."
        p = self._plugins[name]
        if not p.is_enabled():
            return False, f"Plugin '{name}' is disabled."
        entry = p.get_entry()
        if not os.path.isfile(entry):
            return False, f"Plugin '{name}' entry point missing: {entry}"
        try:
            import subprocess
            cmd = [sys.executable, entry] + (args or [])
            result = subprocess.run(cmd, timeout=30)
            return result.returncode == 0, ""
        except Exception as e:
            return False, str(e)

    def get_plugin(self, name: str) -> Plugin:
        return self._plugins.get(name)


# ── Stub generator ────────────────────────────────────────────────────────────

def _generate_stub(spec: dict) -> str:
    name    = spec.get("name", "plugin")
    desc    = spec.get("description", "")
    ptype   = spec.get("type", "tool")
    cmds    = spec.get("commands", [])

    cmd_handlers = "\n".join(
        f'    elif cmd == "{c}":\n        print("[{name}] Running command: {c}")'
        for c in cmds
    )
    if not cmd_handlers:
        cmd_handlers = '    else:\n        print(f"[{name}] Unknown command: {cmd}")'

    return f'''"""
AIOS Plugin: {name}
{desc}
Type: {ptype}
Generated by AIOS Plugin Manager — replace this with real implementation.
"""
import sys


PLUGIN_NAME    = "{name}"
PLUGIN_VERSION = "1.0.0"
PLUGIN_TYPE    = "{ptype}"


def main(args=None):
    args = args or []
    cmd = args[0] if args else "run"

    if cmd == "status":
        print(f"[{{PLUGIN_NAME}}] v{{PLUGIN_VERSION}} — {{PLUGIN_TYPE}} — running")
    elif cmd == "stop":
        print(f"[{{PLUGIN_NAME}}] Stopping...")
{cmd_handlers}


if __name__ == "__main__":
    main(sys.argv[1:])
'''


# Singleton
_pm_lock     = __import__("threading").Lock()
_pm_instance = None


def get_plugin_manager() -> PluginManager:
    global _pm_instance
    if _pm_instance is None:
        with _pm_lock:
            if _pm_instance is None:
                _pm_instance = PluginManager()
    return _pm_instance
