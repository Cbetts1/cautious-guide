"""
AIOS Hub State
Lightweight session persistence for the Studio Hub.

Saves and restores:
  - last active panel
  - last open project id
  - last remote host
  - last comms contact
  - notification queue (unread count per source)

State is stored in ~/.aios/hub_state.json
"""

import json
import os
import time
import threading

_STATE_DIR  = os.path.expanduser("~/.aios")
_STATE_FILE = os.path.join(_STATE_DIR, "hub_state.json")

_DEFAULTS = {
    "last_panel":    "hub",
    "last_project":  None,
    "last_remote":   None,
    "last_contact":  None,
    "notifications": {},
    "updated_at":    None,
}


class HubState:
    """
    Thread-safe key/value store for hub session data.

    Usage::

        from hub.hub_state import get_hub_state
        state = get_hub_state()
        state.set("last_panel", "projects")
        panel = state.get("last_panel")
        state.save()
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._data = dict(_DEFAULTS)
        self._load()

    def _load(self):
        try:
            os.makedirs(_STATE_DIR, exist_ok=True)
            if os.path.isfile(_STATE_FILE):
                with open(_STATE_FILE) as f:
                    saved = json.load(f)
                with self._lock:
                    for k, v in saved.items():
                        self._data[k] = v
        except Exception:
            pass

    def save(self):
        """Persist current state to disk (silent on failure)."""
        try:
            os.makedirs(_STATE_DIR, exist_ok=True)
            with self._lock:
                data = dict(self._data)
            data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            with open(_STATE_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def get(self, key: str, default=None):
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value):
        with self._lock:
            self._data[key] = value

    def add_notification(self, source: str, count: int = 1):
        with self._lock:
            n = self._data.setdefault("notifications", {})
            n[source] = n.get(source, 0) + count

    def clear_notifications(self, source: str = None):
        with self._lock:
            if source:
                self._data.get("notifications", {}).pop(source, None)
            else:
                self._data["notifications"] = {}

    def notification_count(self, source: str = None) -> int:
        with self._lock:
            n = self._data.get("notifications", {})
            if source:
                return n.get(source, 0)
            return sum(n.values())


_hub_state: HubState = None


def get_hub_state() -> HubState:
    global _hub_state
    if _hub_state is None:
        _hub_state = HubState()
    return _hub_state
