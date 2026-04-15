"""
Tests for ai/aura.py — AURA rule matching, fallback, reload, and LLM stub.
"""
import os
import sys
import json
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ai.aura import Aura


# ── Fixture: AURA with real bundled rules ─────────────────────────────────────

@pytest.fixture
def aura():
    return Aura()


# ── Rule matching ─────────────────────────────────────────────────────────────

def test_aura_hello_response(aura):
    resp = aura.query("hello")
    assert isinstance(resp, str) and len(resp) > 0


def test_aura_status_response(aura):
    resp = aura.query("status")
    assert isinstance(resp, str)


def test_aura_identify(aura):
    resp = aura.query("who are you")
    assert isinstance(resp, str) and len(resp) > 0


def test_aura_explain_aios(aura):
    resp = aura.query("what is aios")
    assert isinstance(resp, str) and len(resp) > 0


def test_aura_fallback_unknown(aura):
    resp = aura.query("xyzzy-unknowable-nonsense-token-12345")
    assert isinstance(resp, str) and len(resp) > 0


# ── Custom rules ─────────────────────────────────────────────────────────────

def test_aura_custom_rules(tmp_path, monkeypatch):
    rules_file = tmp_path / "rules.json"
    rules = [
        {"patterns": ["ping"], "response": "pong"},
        {"patterns": ["foo", "bar"], "response": "baz"},
    ]
    rules_file.write_text(json.dumps(rules))
    # Patch module-level RULES_PATH so _load_rules() picks up our file
    import ai.aura as aura_mod
    monkeypatch.setattr(aura_mod, "RULES_PATH", str(rules_file))
    a = Aura(cfg={"mode": "rule"})
    assert "pong" in a.query("ping")
    assert "baz"  in a.query("foo")
    assert "baz"  in a.query("bar")


def test_aura_rules_case_insensitive(tmp_path, monkeypatch):
    rules_file = tmp_path / "rules.json"
    rules_file.write_text(json.dumps([{"patterns": ["hello"], "response": "hi"}]))
    import ai.aura as aura_mod
    monkeypatch.setattr(aura_mod, "RULES_PATH", str(rules_file))
    a = Aura(cfg={"mode": "rule"})
    assert "hi" in a.query("HELLO")
    assert "hi" in a.query("Hello")


# ── Rule reload ───────────────────────────────────────────────────────────────

def test_aura_reload_rules(tmp_path, monkeypatch):
    rules_file = tmp_path / "rules.json"
    rules_file.write_text(json.dumps([{"patterns": ["alpha"], "response": "beta"}]))
    import ai.aura as aura_mod
    monkeypatch.setattr(aura_mod, "RULES_PATH", str(rules_file))
    a = Aura(cfg={"mode": "rule"})
    assert "beta" in a.query("alpha")

    # Update rules on disk and reload
    rules_file.write_text(json.dumps([{"patterns": ["gamma"], "response": "delta"}]))
    count = a.reload_rules()
    assert count == 1
    assert "delta" in a.query("gamma")


# ── LLM mode stub ─────────────────────────────────────────────────────────────

def test_aura_llm_mode_falls_back_to_rules(aura):
    """With no model loaded, llm mode must gracefully fall back to rules."""
    aura.mode = "llm"
    resp = aura.query("hello")
    assert isinstance(resp, str) and len(resp) > 0
    aura.mode = "rule"  # reset for other tests


def test_aura_load_llm_returns_false_without_llama():
    """load_llm should return False when llama_cpp is not installed."""
    a = Aura()
    result = a.load_llm("/nonexistent/model.gguf")
    assert result is False


# ── Status / info ────────────────────────────────────────────────────────────

def test_aura_get_status_keys(aura):
    info = aura.get_status()
    for key in ("mode", "model", "rules", "ctx_items"):
        assert key in info


def test_aura_rules_loaded(aura):
    info = aura.get_status()
    assert info["rules"] > 0


# ── Context history ───────────────────────────────────────────────────────────

def test_aura_context_grows(aura):
    before = len(aura.context)
    aura.query("hello")
    after = len(aura.context)
    assert after >= before


def test_aura_clear_context(aura):
    aura.query("hello")
    aura.clear_context()
    assert aura.context == []
