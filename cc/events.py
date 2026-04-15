"""
AIOS EventBus
Global singleton for system-wide event logging and auditing.
All AIOS subsystems emit events here; the Events panel displays them live.
"""

import time
import threading
from typing import Callable, List, Optional

# ── Event levels ──────────────────────────────────────────────────────────────
LEVEL_OK    = "OK"
LEVEL_WARN  = "WARN"
LEVEL_ERROR = "ERROR"
LEVEL_INFO  = "INFO"

_LEVEL_ORDER = {LEVEL_OK: 0, LEVEL_INFO: 1, LEVEL_WARN: 2, LEVEL_ERROR: 3}


class Event:
    def __init__(self, source: str, level: str, message: str):
        self.source    = source
        self.level     = level
        self.message   = message
        self.timestamp = time.time()
        self.ts_str    = time.strftime("%H:%M:%S", time.localtime(self.timestamp))

    def __str__(self) -> str:
        return f"[{self.ts_str}] [{self.level:<5}] {self.source}: {self.message}"


class EventBus:
    """
    Thread-safe event bus.
    - emit(source, level, message)  — publish an event
    - subscribe(callback)           — called on every new event
    - get_events(n)                 — return last n events
    - clear()                       — wipe log
    """

    MAX_EVENTS = 500

    def __init__(self):
        self._events: List[Event] = []
        self._subscribers: List[Callable[[Event], None]] = []
        self._lock = threading.Lock()

    def emit(self, source: str, level: str, message: str):
        """Publish an event to all subscribers and the internal log."""
        ev = Event(source, level, message)
        with self._lock:
            self._events.append(ev)
            if len(self._events) > self.MAX_EVENTS:
                self._events = self._events[-self.MAX_EVENTS:]
            subs = list(self._subscribers)
        for cb in subs:
            try:
                cb(ev)
            except Exception:
                pass

    def subscribe(self, callback: Callable[[Event], None]):
        """Register a callback to receive every new event."""
        with self._lock:
            if callback not in self._subscribers:
                self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[Event], None]):
        with self._lock:
            self._subscribers = [s for s in self._subscribers if s != callback]

    def get_events(self, n: int = 100, min_level: Optional[str] = None) -> List[Event]:
        """Return the last n events, optionally filtered by minimum level."""
        with self._lock:
            events = list(self._events)
        if min_level:
            threshold = _LEVEL_ORDER.get(min_level, 0)
            events = [e for e in events if _LEVEL_ORDER.get(e.level, 0) >= threshold]
        return events[-n:]

    def clear(self):
        with self._lock:
            self._events.clear()

    def count(self) -> int:
        with self._lock:
            return len(self._events)


# ── Singleton ─────────────────────────────────────────────────────────────────

_event_bus_lock: __import__("threading").Lock = __import__("threading").Lock()
_event_bus: Optional[EventBus] = None
_event_bus_lock = threading.Lock()


def get_event_bus() -> EventBus:
    global _event_bus
    if _event_bus is None:
        with _event_bus_lock:
            if _event_bus is None:
                _event_bus = EventBus()
    return _event_bus
