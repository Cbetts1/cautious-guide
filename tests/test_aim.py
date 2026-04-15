"""
Tests for aim/aim.py — URL validation, queue cap, and basic AIM behaviour.
"""
import os
import sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aim.aim import AIM, _validate_external_url, AIMRequest


# ── URL validation ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("url", [
    "http://example.com",
    "https://httpbin.org/get",
    "https://api.github.com/",
])
def test_valid_public_urls(url):
    assert _validate_external_url(url) == ""


@pytest.mark.parametrize("url,reason", [
    ("http://localhost/",       "loopback"),
    ("http://127.0.0.1/",       "loopback"),
    ("http://127.1.2.3/",       "loopback"),
    ("http://192.168.1.1/",     "private"),
    ("http://10.0.0.1/",        "private"),
    ("http://172.16.0.1/",      "private"),
    ("http://0.0.0.0/",         "blocked"),
    ("ftp://example.com",       "scheme"),
    ("file:///etc/passwd",      "scheme"),
])
def test_blocked_urls(url, reason):
    err = _validate_external_url(url)
    assert err != "", f"Expected URL '{url}' to be blocked ({reason}), but got empty error"


# ── AIM offline queue ─────────────────────────────────────────────────────────

def test_aim_queue_max_size():
    """Queue must not exceed QUEUE_MAX_SIZE; oldest entry should be dropped."""
    aim = AIM()
    aim._online = False

    cap = AIM.QUEUE_MAX_SIZE
    # Fill the queue beyond the cap
    for i in range(cap + 10):
        aim.fetch(f"https://example.com/page/{i}")

    assert len(aim._queue) == cap


def test_aim_queue_drops_oldest():
    """When the queue is at cap, the oldest request is replaced."""
    aim = AIM()
    aim._online = False

    cap = AIM.QUEUE_MAX_SIZE
    aim._queue = [AIMRequest(f"https://example.com/old/{i}") for i in range(cap)]
    # The very first item in the queue should be /old/0
    aim.fetch("https://example.com/newest")
    # After adding one more: /old/0 is gone, /newest is last
    assert aim._queue[-1].url == "https://example.com/newest"
    assert aim._queue[0].url != "https://example.com/old/0"


def test_aim_fetch_queued_when_offline():
    aim = AIM()
    aim._online = False
    result = aim.fetch("https://example.com")
    assert result["ok"] is False
    assert "queued" in result["error"]
    assert len(aim._queue) == 1


def test_aim_post_queued_when_offline():
    aim = AIM()
    aim._online = False
    result = aim.post("https://example.com/api", {"key": "value"})
    assert result["ok"] is False
    assert "queued" in result["error"]


# ── AIM status ────────────────────────────────────────────────────────────────

def test_aim_status_keys():
    aim = AIM()
    status = aim.get_status()
    for key in ("version", "online", "queued", "enabled"):
        assert key in status


def test_aim_is_online_default_false():
    aim = AIM()
    # Without starting the monitor thread the default is False
    assert aim.is_online() is False


# ── AIM blocked fetch ─────────────────────────────────────────────────────────

def test_aim_fetch_blocks_private_ip():
    aim = AIM()
    aim._online = True  # pretend we're online
    result = aim.fetch("http://192.168.0.1/secret")
    assert result["ok"] is False
    assert result["error"] != ""
