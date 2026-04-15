"""
Tests for projects/registry.py — CRUD, filtering, and persistence.
"""
import os
import sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import projects.registry as _module
from projects.registry import ProjectRegistry, STATUS_DRAFT, STATUS_RUNNING


@pytest.fixture
def reg(tmp_path, monkeypatch):
    """Isolated ProjectRegistry backed by a temp file."""
    projects_file = str(tmp_path / "projects.json")
    monkeypatch.setattr(_module, "_PROJECTS_FILE", projects_file)
    monkeypatch.setattr(_module, "_STATE_DIR", str(tmp_path))
    return ProjectRegistry()


# ── create ────────────────────────────────────────────────────────────────────

def test_create_returns_id(reg):
    pid = reg.create("My AI", "ai")
    assert isinstance(pid, str) and len(pid) == 8


def test_create_stores_record(reg):
    pid = reg.create("Test Proj", "server")
    rec = reg.get(pid)
    assert rec is not None
    assert rec["name"] == "Test Proj"
    assert rec["type"] == "server"
    assert rec["status"] == STATUS_DRAFT


def test_create_unknown_type_defaults_to_other(reg):
    pid = reg.create("Oddball", "banana")
    assert reg.get(pid)["type"] == "other"


# ── get ───────────────────────────────────────────────────────────────────────

def test_get_nonexistent(reg):
    assert reg.get("deadbeef") is None


def test_get_returns_copy(reg):
    """Mutating the returned dict must not affect the stored record."""
    pid = reg.create("Immutable", "ai")
    copy = reg.get(pid)
    copy["name"] = "CHANGED"
    assert reg.get(pid)["name"] == "Immutable"


# ── update ────────────────────────────────────────────────────────────────────

def test_update_status(reg):
    pid = reg.create("Running", "service")
    ok = reg.update(pid, status=STATUS_RUNNING)
    assert ok is True
    assert reg.get(pid)["status"] == STATUS_RUNNING


def test_update_nonexistent(reg):
    ok = reg.update("ffffffff", status="running")
    assert ok is False


# ── delete ────────────────────────────────────────────────────────────────────

def test_delete_existing(reg):
    pid = reg.create("ToDelete", "ai")
    ok = reg.delete(pid)
    assert ok is True
    assert reg.get(pid) is None


def test_delete_nonexistent(reg):
    ok = reg.delete("00000000")
    assert ok is False


# ── list_all ──────────────────────────────────────────────────────────────────

def test_list_all_empty(reg):
    assert reg.list_all() == []


def test_list_all_sorted_newest_first(tmp_path, monkeypatch):
    """list_all() should return most-recently created project first."""
    projects_file = str(tmp_path / "projects.json")
    monkeypatch.setattr(_module, "_PROJECTS_FILE", projects_file)
    monkeypatch.setattr(_module, "_STATE_DIR", str(tmp_path))

    import projects.registry as pr_mod

    # Monkeypatch _now() to return distinct timestamps
    timestamps = iter(["2024-01-01T00:00:01", "2024-01-01T00:00:02"])
    monkeypatch.setattr(pr_mod, "_now", lambda: next(timestamps))

    reg = ProjectRegistry()
    reg.create("First", "ai")
    pid2 = reg.create("Second", "os")
    items = reg.list_all()
    assert items[0]["id"] == pid2


# ── list_by_type / list_by_status ────────────────────────────────────────────

def test_list_by_type(reg):
    reg.create("Srv1", "server")
    reg.create("AI1",  "ai")
    servers = reg.list_by_type("server")
    assert all(p["type"] == "server" for p in servers)
    assert len(servers) == 1


def test_list_by_status(reg):
    pid1 = reg.create("Running", "service")
    reg.create("Draft",   "service")
    reg.update(pid1, status=STATUS_RUNNING)
    running = reg.list_by_status(STATUS_RUNNING)
    assert len(running) == 1
    assert running[0]["id"] == pid1


# ── count ─────────────────────────────────────────────────────────────────────

def test_count(reg):
    assert reg.count() == 0
    reg.create("P1", "ai")
    reg.create("P2", "ai")
    assert reg.count() == 2


# ── persistence ───────────────────────────────────────────────────────────────

def test_persistence(tmp_path, monkeypatch):
    """Records survive across ProjectRegistry instances."""
    projects_file = str(tmp_path / "projects.json")
    monkeypatch.setattr(_module, "_PROJECTS_FILE", projects_file)
    monkeypatch.setattr(_module, "_STATE_DIR", str(tmp_path))

    r1 = ProjectRegistry()
    pid = r1.create("Persisted", "cloud")

    r2 = ProjectRegistry()
    assert r2.get(pid) is not None
    assert r2.get(pid)["name"] == "Persisted"
