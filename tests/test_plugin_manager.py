"""
Tests for plugins/plugin_manager.py — install, remove, list, enable/disable.
"""
import os
import sys
import json
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import plugins.plugin_manager as _pm_mod
from plugins.plugin_manager import PluginManager


@pytest.fixture
def pm_env(tmp_path, monkeypatch):
    """
    Set up a temporary plugin environment and return a PluginManager
    rooted in it.  Monkeypatches module-level constants so the real
    __init__ uses the temp paths.
    """
    installed_dir  = tmp_path / "plugins" / "installed"
    installed_dir.mkdir(parents=True)
    registry_file  = tmp_path / "plugins" / "registry.json"

    registry = {
        "available": [
            {
                "name": "testplugin",
                "version": "1.0.0",
                "description": "A test plugin",
                "type": "tool",
                "bundled": True,
                "requires": [],
                "commands": ["run"],
            }
        ]
    }
    registry_file.write_text(json.dumps(registry))

    monkeypatch.setattr(_pm_mod, "INSTALLED",       str(installed_dir))
    monkeypatch.setattr(_pm_mod, "REGISTRY_PATH",   str(registry_file))

    return PluginManager()


# ── list_available ────────────────────────────────────────────────────────────

def test_list_available(pm_env):
    avail = pm_env.list_available()
    names = [p["name"] for p in avail]
    assert "testplugin" in names


# ── install / list_installed ──────────────────────────────────────────────────

def test_install_and_list(pm_env):
    ok, msg = pm_env.install("testplugin")
    assert ok is True, msg
    installed = pm_env.list_installed()
    names = [p["name"] for p in installed]
    assert "testplugin" in names


def test_install_already_installed(pm_env):
    pm_env.install("testplugin")
    ok, msg = pm_env.install("testplugin")
    assert ok is False


def test_install_nonexistent(pm_env):
    ok, msg = pm_env.install("ghost-plugin")
    assert ok is False


# ── remove ────────────────────────────────────────────────────────────────────

def test_remove_installed(pm_env):
    pm_env.install("testplugin")
    ok, msg = pm_env.remove("testplugin")
    assert ok is True
    names = [p["name"] for p in pm_env.list_installed()]
    assert "testplugin" not in names


def test_remove_nonexistent(pm_env):
    ok, msg = pm_env.remove("ghost-plugin")
    assert ok is False


# ── enable / disable ──────────────────────────────────────────────────────────

def test_disable_and_enable(pm_env):
    pm_env.install("testplugin")
    ok_d, _ = pm_env.disable("testplugin")
    assert ok_d is True
    ok_e, _ = pm_env.enable("testplugin")
    assert ok_e is True


def test_plugin_is_enabled_true_by_default(pm_env):
    pm_env.install("testplugin")
    plug = pm_env._plugins.get("testplugin")
    assert plug is not None
    assert plug.is_enabled() is True


def test_plugin_is_enabled_false_after_disable(pm_env):
    pm_env.install("testplugin")
    pm_env.disable("testplugin")
    plug = pm_env._plugins.get("testplugin")
    assert plug is not None
    assert plug.is_enabled() is False


# ── is_installed ──────────────────────────────────────────────────────────────

def test_is_installed_true(pm_env):
    pm_env.install("testplugin")
    assert pm_env.is_installed("testplugin") is True


def test_is_installed_false(pm_env):
    assert pm_env.is_installed("ghost") is False
