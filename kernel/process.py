"""
AIOS Process Registry
Tracks AIOS-managed background services and daemons.
"""

import time
import os
from typing import Optional


class ServiceEntry:
    def __init__(self, name: str, pid: int, description: str = ""):
        self.name        = name
        self.pid         = pid
        self.description = description
        self.started_at  = time.time()
        self.status      = "running"

    def is_alive(self) -> bool:
        if self.pid <= 0:
            return self.status == "running"
        try:
            os.kill(self.pid, 0)
            return True
        except OSError:
            return False

    def to_dict(self) -> dict:
        return {
            "name":        self.name,
            "pid":         self.pid,
            "description": self.description,
            "started_at":  time.strftime("%H:%M:%S", time.localtime(self.started_at)),
            "status":      "running" if self.is_alive() else "stopped",
        }


class ProcessRegistry:
    def __init__(self):
        self._services: dict[str, ServiceEntry] = {}

    def register(self, name: str, pid: int, description: str = ""):
        self._services[name] = ServiceEntry(name, pid, description)

    def unregister(self, name: str):
        self._services.pop(name, None)

    def get(self, name: str) -> Optional[ServiceEntry]:
        return self._services.get(name)

    def list(self) -> list:
        return [s.to_dict() for s in self._services.values()]

    def running_count(self) -> int:
        return sum(1 for s in self._services.values() if s.is_alive())

    def total_count(self) -> int:
        return len(self._services)
