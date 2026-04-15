"""
AIOS Event Bus
Global event log for Command Center panels and all AIOS subsystems.
Lightweight circular buffer — no external dependencies.

Usage:
    from cc.events import get_event_bus, LEVEL_OK, LEVEL_WARN, LEVEL_ERROR, LEVEL_INFO
    get_event_bus().emit("MySource", LEVEL_OK, "Something happened")
"""

import time
import threading

LEVEL_INFO  = "INFO"
LEVEL_OK    = "OK"
LEVEL_WARN  = "WARN"
LEVEL_ERROR = "ERROR"

MAX_EVENTS = 300


class Event:
    __slots__ = ("ts", "source", "level", "message")

    def __init__(self, source: str, level: str, message: str):
        self.ts      = time.time()
        self.source  = source
        self.level   = level
        self.message = message

    def ts_str(self) -> str:
        return time.strftime("%H:%M:%S", time.localtime(self.ts))

    def __repr__(self) -> str:
        return f"<Event {self.ts_str()} [{self.level}] {self.source}: {self.message}>"


class EventBus:
    """Thread-safe circular event buffer."""

    def __init__(self):
        self._events: list = []
        self._lock   = threading.Lock()

    def emit(self, source: str, level: str, message: str):
        """Append a new event to the bus."""
        ev = Event(source, level, message)
        with self._lock:
            self._events.append(ev)
            if len(self._events) > MAX_EVENTS:
                self._events = self._events[-MAX_EVENTS:]

    def recent(self, n: int = 30) -> list:
        """Return the n most recent events (oldest first)."""
        with self._lock:
            return list(self._events[-n:])

    def all(self) -> list:
        """Return all stored events."""
        with self._lock:
            return list(self._events)

    def count(self) -> int:
        with self._lock:
            return len(self._events)

    def clear(self):
        with self._lock:
            self._events.clear()


# ── Singleton ─────────────────────────────────────────────────────────────────

_bus: "EventBus | None" = None


def get_event_bus() -> EventBus:
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus
