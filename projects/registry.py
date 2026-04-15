"""
AIOS Project Registry
Persistent store for AIOS project metadata.

Projects are saved to ~/.aios/projects.json

Each project record:
  id          str   — UUID-like short identifier
  name        str
  type        str   — ai | os | vm | server | website | cloud | remote_agent
  status      str   — draft | building | running | stopped | error
  path        str   — local filesystem path (optional)
  target      str   — deployment/run target description
  provider    str   — provider id (optional)
  notes       str
  created_at  str   — ISO timestamp
  updated_at  str
  last_build  str   — ISO timestamp or None
  last_run    str   — ISO timestamp or None
  tags        list[str]
"""

import json
import os
import time
import uuid
import threading

_STATE_DIR     = os.path.expanduser("~/.aios")
_PROJECTS_FILE = os.path.join(_STATE_DIR, "projects.json")

# Valid project types
PROJECT_TYPES = [
    "ai",
    "os",
    "vm",
    "server",
    "website",
    "cloud",
    "remote_agent",
    "plugin",
    "service",
    "other",
]

# Valid status values
STATUS_DRAFT    = "draft"
STATUS_BUILDING = "building"
STATUS_RUNNING  = "running"
STATUS_STOPPED  = "stopped"
STATUS_ERROR    = "error"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


class ProjectRegistry:
    """
    Thread-safe CRUD store for AIOS project records.

    Usage::

        from projects.registry import get_registry
        reg = get_registry()
        pid = reg.create("My AI", "ai")
        reg.update(pid, status="running")
        projects = reg.list_all()
        reg.delete(pid)
    """

    def __init__(self):
        self._lock     = threading.Lock()
        self._projects = {}   # id → record dict
        self._load()

    # ── Persistence ────────────────────────────────────────────────────

    def _load(self):
        try:
            os.makedirs(_STATE_DIR, exist_ok=True)
            if os.path.isfile(_PROJECTS_FILE):
                with open(_PROJECTS_FILE) as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    with self._lock:
                        self._projects = data
        except Exception:
            pass

    def save(self):
        """Persist registry to disk (silent on failure)."""
        try:
            os.makedirs(_STATE_DIR, exist_ok=True)
            with self._lock:
                data = dict(self._projects)
            with open(_PROJECTS_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    # ── CRUD ───────────────────────────────────────────────────────────

    def create(self, name: str, project_type: str = "other",
               path: str = "", notes: str = "") -> str:
        """Create a new project record. Returns the new project id."""
        pid = _new_id()
        now = _now()
        record = {
            "id":         pid,
            "name":       name,
            "type":       project_type if project_type in PROJECT_TYPES else "other",
            "status":     STATUS_DRAFT,
            "path":       path,
            "target":     "",
            "provider":   "",
            "notes":      notes,
            "created_at": now,
            "updated_at": now,
            "last_build": None,
            "last_run":   None,
            "tags":       [],
        }
        with self._lock:
            self._projects[pid] = record
        self.save()
        try:
            from cc.events import get_event_bus, LEVEL_OK
            get_event_bus().emit("projects", LEVEL_OK,
                                 f"Project created: {name} ({project_type})")
        except Exception:
            pass
        return pid

    def get(self, pid: str) -> dict:
        """Return a copy of the project record, or None if not found."""
        with self._lock:
            rec = self._projects.get(pid)
            return dict(rec) if rec else None

    def update(self, pid: str, **kwargs) -> bool:
        """Update fields on an existing project. Returns True on success."""
        with self._lock:
            if pid not in self._projects:
                return False
            rec = self._projects[pid]
            for k, v in kwargs.items():
                if k in rec:
                    rec[k] = v
            rec["updated_at"] = _now()
        self.save()
        return True

    def delete(self, pid: str) -> bool:
        """Remove a project record. Returns True if it existed."""
        with self._lock:
            existed = pid in self._projects
            self._projects.pop(pid, None)
        if existed:
            self.save()
        return existed

    def list_all(self) -> list:
        """Return a list of all project records (copies), newest first."""
        with self._lock:
            records = [dict(r) for r in self._projects.values()]
        records.sort(key=lambda r: r.get("updated_at", ""), reverse=True)
        return records

    def list_by_type(self, project_type: str) -> list:
        return [r for r in self.list_all() if r["type"] == project_type]

    def list_by_status(self, status: str) -> list:
        return [r for r in self.list_all() if r["status"] == status]

    def count(self) -> int:
        with self._lock:
            return len(self._projects)


# ── Singleton ──────────────────────────────────────────────────────────────────

_registry_lock: __import__("threading").Lock = __import__("threading").Lock()
_registry: ProjectRegistry = None


def get_registry() -> ProjectRegistry:
    global _registry
    if _registry is None:
        with _registry_lock:
            if _registry is None:
                _registry = ProjectRegistry()
    return _registry
