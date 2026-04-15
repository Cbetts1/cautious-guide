"""
Tests for auth/pin_auth.py — PBKDF2-HMAC hashing, credential storage,
legacy SHA-256 migration, and PinAuth.authenticate() logic.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import auth.pin_auth as _module


# ── Hash helpers ──────────────────────────────────────────────────────────────

def test_hash_pin_returns_string():
    h = _module._hash_pin("1234", "somesalt")
    assert isinstance(h, str)


def test_hash_pin_deterministic():
    h1 = _module._hash_pin("5678", "salt1")
    h2 = _module._hash_pin("5678", "salt1")
    assert h1 == h2


def test_hash_pin_different_pins():
    h1 = _module._hash_pin("0000", "salt")
    h2 = _module._hash_pin("1111", "salt")
    assert h1 != h2


def test_hash_pin_different_salts():
    h1 = _module._hash_pin("1234", "saltA")
    h2 = _module._hash_pin("1234", "saltB")
    assert h1 != h2


def test_hash_pin_not_plaintext():
    h = _module._hash_pin("1234", "salt")
    assert "1234" not in h


# ── Credential storage in ~/.aios/auth.json ───────────────────────────────────

def test_save_and_load_auth(tmp_aios_home, monkeypatch):
    monkeypatch.setattr(_module, "AUTH_PATH", str(tmp_aios_home / "auth.json"))
    data = {"version": "pbkdf2-sha256-v1", "pin_hash": "aabbcc", "pin_salt": "mysalt"}
    _module._save_auth(data)
    loaded = _module._load_auth()
    assert loaded == data


def test_load_auth_missing_returns_empty(tmp_aios_home, monkeypatch):
    monkeypatch.setattr(_module, "AUTH_PATH", str(tmp_aios_home / "nofile.json"))
    assert _module._load_auth() == {}


# ── Legacy migration ──────────────────────────────────────────────────────────

def test_migrate_legacy_moves_credentials(tmp_aios_home, monkeypatch, tmp_path):
    monkeypatch.setattr(_module, "AUTH_PATH", str(tmp_aios_home / "auth.json"))
    # Create a fake config that still has pin_hash / pin_salt
    cfg_path = tmp_path / "config" / "aios.cfg"
    cfg_path.parent.mkdir()
    cfg = {"auth": {"pin_required": True, "pin_hash": "deadbeef", "pin_salt": "salty"}}
    cfg_path.write_text(json.dumps(cfg))
    monkeypatch.setattr(_module, "CFG_PATH", str(cfg_path))

    migrated = _module._migrate_legacy_credentials(cfg)
    assert migrated is True

    # Credentials should now be in auth.json, not in config
    auth_data = _module._load_auth()
    assert auth_data.get("pin_hash") == "deadbeef"
    assert auth_data.get("version") == "sha256-legacy"

    saved_cfg = json.loads(cfg_path.read_text())
    assert "pin_hash" not in saved_cfg.get("auth", {})
    assert "pin_salt" not in saved_cfg.get("auth", {})


def test_migrate_legacy_noop_when_no_credentials(tmp_aios_home, monkeypatch, tmp_path):
    monkeypatch.setattr(_module, "AUTH_PATH", str(tmp_aios_home / "auth.json"))
    cfg = {"auth": {"pin_required": True}}
    migrated = _module._migrate_legacy_credentials(cfg)
    assert migrated is False


# ── PinAuth._verify_pin ───────────────────────────────────────────────────────

def _make_auth(tmp_aios_home, monkeypatch, pin: str, version: str = "pbkdf2-sha256-v1"):
    """Set up PinAuth with a known PIN in auth.json and return the instance."""
    auth_path = str(tmp_aios_home / "auth.json")
    monkeypatch.setattr(_module, "AUTH_PATH", auth_path)
    # Write cfg without credentials
    monkeypatch.setattr(_module, "CFG_PATH", "/dev/null")

    import secrets
    salt = secrets.token_hex(16)
    if version == "pbkdf2-sha256-v1":
        hashed = _module._hash_pin(pin, salt)
    else:
        import hashlib
        hashed = hashlib.sha256((salt + pin).encode()).hexdigest()

    _module._save_auth({"version": version, "pin_hash": hashed, "pin_salt": salt})

    pa = _module.PinAuth.__new__(_module.PinAuth)
    pa.cfg          = {"auth": {"pin_required": True, "max_attempts": 5}}
    pa.auth_cfg     = pa.cfg["auth"]
    pa.max_attempts = 5
    pa._auth_data   = _module._load_auth()
    return pa


def test_verify_correct_pin(tmp_aios_home, monkeypatch):
    pa = _make_auth(tmp_aios_home, monkeypatch, "4321")
    assert pa._verify_pin("4321") is True


def test_verify_wrong_pin(tmp_aios_home, monkeypatch):
    pa = _make_auth(tmp_aios_home, monkeypatch, "4321")
    assert pa._verify_pin("9999") is False


def test_verify_legacy_pin_and_upgrade(tmp_aios_home, monkeypatch):
    """Legacy SHA-256 PIN verifies successfully and is auto-upgraded to pbkdf2."""
    pa = _make_auth(tmp_aios_home, monkeypatch, "1234", version="sha256-legacy")
    assert pa._is_legacy_hash() is True
    assert pa._verify_pin("1234") is True
    # After verify, the stored hash should be the new format
    assert pa._auth_data.get("version") == "pbkdf2-sha256-v1"


def test_verify_legacy_wrong_pin(tmp_aios_home, monkeypatch):
    pa = _make_auth(tmp_aios_home, monkeypatch, "1234", version="sha256-legacy")
    assert pa._verify_pin("9999") is False


# ── PinAuth.authenticate — auth disabled ─────────────────────────────────────

def test_authenticate_disabled(tmp_aios_home, monkeypatch):
    monkeypatch.setattr(_module, "AUTH_PATH", str(tmp_aios_home / "auth.json"))
    monkeypatch.setattr(_module, "CFG_PATH", "/dev/null")
    pa = _module.PinAuth.__new__(_module.PinAuth)
    pa.cfg          = {"auth": {"pin_required": False}}
    pa.auth_cfg     = pa.cfg["auth"]
    pa.max_attempts = 5
    pa._auth_data   = {}
    assert pa.authenticate() is True
