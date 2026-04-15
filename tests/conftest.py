"""
Shared pytest fixtures for the AIOS test suite.
"""
import os
import sys
import json
import pytest

# Ensure AIOS root is on sys.path regardless of where pytest is invoked from
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


@pytest.fixture
def tmp_aios_home(tmp_path, monkeypatch):
    """
    Redirect ~/.aios/ to a temporary directory so tests are hermetic and
    never touch real user state.
    """
    aios_dir = tmp_path / ".aios"
    aios_dir.mkdir()
    monkeypatch.setenv("HOME", str(tmp_path))
    return aios_dir


@pytest.fixture
def tmp_cfg(tmp_path):
    """Write a minimal aios.cfg and return its path."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    cfg = {
        "system": {"name": "AIOS-test", "locale": "en"},
        "auth":   {"pin_required": True, "max_attempts": 5},
        "aim":    {"enabled": True},
        "aura":   {"mode": "rules"},
        "services": {"autostart": []},
    }
    cfg_path = config_dir / "aios.cfg"
    cfg_path.write_text(json.dumps(cfg, indent=2))
    return str(cfg_path)
