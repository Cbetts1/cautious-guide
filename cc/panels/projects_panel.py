"""CC Panel: Projects — create and manage AIOS projects."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_TYPE_LABELS = {
    "ai":           "AI Assistant",
    "os":           "OS Layer",
    "vm":           "VM Profile",
    "server":       "Server",
    "website":      "Website",
    "cloud":        "Cloud Target",
    "remote_agent": "Remote Agent",
    "plugin":       "Plugin",
    "service":      "Service",
    "other":        "Other",
}

_STATUS_COLORS = {
    "draft":    7,   # yellow
    "building": 1,   # cyan
    "running":  5,   # green
    "stopped":  2,   # white
    "error":    6,   # red
}


class ProjectsPanel:
    TITLE = "PROJECTS"

    def __init__(self):
        self._sel = 0
        self._msg = ""

    def render(self, win, y: int, x: int, height: int, width: int,
               kal=None, curses_mod=None):
        c = curses_mod
        row = y

        def addline(text, attr=0):
            nonlocal row
            if row < y + height - 1:
                try:
                    win.addnstr(row, x, text, width - 1, attr)
                except Exception:
                    pass
                row += 1

        try:
            from projects.registry import get_registry
            reg      = get_registry()
            projects = reg.list_all()

            addline("  AIOS PROJECT MANAGER", c.color_pair(1) | c.A_BOLD)
            addline(f"  {reg.count()} project(s)   "
                    "↑/↓ navigate  N new  D delete  | " + self._msg,
                    c.color_pair(2))
            addline("  " + "─" * (width - 4), c.color_pair(8))
            addline("")

            if not projects:
                addline("  No projects yet.  Press N to create one.", c.color_pair(7))
                addline("")
                addline("  Project types:", c.A_BOLD)
                for t, label in _TYPE_LABELS.items():
                    addline(f"    ◈ {label}")
                return

            # Clamp selection
            if self._sel >= len(projects):
                self._sel = max(0, len(projects) - 1)

            hdr = f"  {'NAME':<20} {'TYPE':<14} {'STATUS':<10} {'UPDATED'}"
            addline(hdr, c.A_BOLD)
            addline("  " + "─" * (width - 4), c.color_pair(8))

            for i, p in enumerate(projects):
                type_label   = _TYPE_LABELS.get(p["type"], p["type"])
                status       = p.get("status", "draft")
                status_color = _STATUS_COLORS.get(status, 2)
                is_sel       = (i == self._sel)

                name    = p["name"][:18]
                updated = (p.get("updated_at") or "")[:16]

                if is_sel:
                    attr = c.color_pair(3) | c.A_BOLD | c.A_REVERSE
                else:
                    attr = c.color_pair(status_color)

                line = f"  {name:<20} {type_label:<14} {status:<10} {updated}"
                addline(line[:width - 2], attr)

            # Detail pane for selected project
            addline("")
            if projects and self._sel < len(projects):
                p = projects[self._sel]
                addline("  SELECTED PROJECT", c.A_BOLD)
                addline(f"    ID      : {p['id']}")
                addline(f"    Name    : {p['name']}")
                addline(f"    Type    : {_TYPE_LABELS.get(p['type'], p['type'])}")
                addline(f"    Status  : {p['status']}")
                if p.get("path"):
                    addline(f"    Path    : {p['path'][:width - 16]}")
                if p.get("notes"):
                    addline(f"    Notes   : {p['notes'][:width - 16]}")
                addline(f"    Created : {(p.get('created_at') or '')[:16]}")

        except Exception as e:
            try:
                win.addnstr(y, x, f"  Projects panel error: {e}", width - 1,
                            curses_mod.color_pair(6) if curses_mod else 0)
            except Exception:
                pass

    def handle_key(self, key, curses_mod=None):
        c = curses_mod
        try:
            from projects.registry import get_registry
            reg      = get_registry()
            projects = reg.list_all()

            if key == c.KEY_UP:
                self._sel = max(0, self._sel - 1)
                self._msg = ""
            elif key == c.KEY_DOWN:
                self._sel = min(max(0, len(projects) - 1), self._sel + 1)
                self._msg = ""
            elif key in (ord("n"), ord("N")):
                self._create_demo_project(reg)
            elif key in (ord("d"), ord("D")):
                if projects and self._sel < len(projects):
                    p = projects[self._sel]
                    reg.delete(p["id"])
                    self._sel = max(0, self._sel - 1)
                    self._msg = f"Deleted: {p['name']}"
                    from hub.hub_state import get_hub_state
                    if get_hub_state().get("last_project") == p["id"]:
                        get_hub_state().set("last_project", None)
        except Exception as e:
            self._msg = f"Error: {e}"

    def _create_demo_project(self, reg):
        """Create a demo project to show the system works."""
        from projects.registry import PROJECT_TYPES
        # Cycle through types so demos are varied
        projects = reg.list_all()
        type_idx = len(projects) % len(PROJECT_TYPES)
        ptype = PROJECT_TYPES[type_idx]
        name  = f"New {ptype.replace('_', ' ').title()} {len(projects) + 1}"
        pid   = reg.create(name, ptype, notes="Created from Projects panel")
        from hub.hub_state import get_hub_state
        get_hub_state().set("last_project", pid)
        get_hub_state().save()
        self._msg = f"Created: {name}"
        try:
            from cc.events import get_event_bus, LEVEL_OK
            get_event_bus().emit("projects_panel", LEVEL_OK,
                                 f"Project created: {name}")
        except Exception:
            pass
