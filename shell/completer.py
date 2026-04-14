"""
AIOS ARROW Shell — Tab Completion
Provides readline-based completion for built-in commands,
plugin names, and file paths.
"""

import os
import readline

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BUILTIN_COMMANDS = [
    "sysinfo",
    "aios",
    "aios install",
    "aios remove",
    "aios list",
    "aios list installed",
    "aios list available",
    "aios enable",
    "aios disable",
    "aios status",
    "aios update",
    "aura",
    "aim",
    "aim status",
    "aim check",
    "aim fetch",
    "services",
    "arrow",
    "arrow build service",
    "arrow build plugin",
    "arrow build layer",
    "cc",
    "clear",
    "exit",
    "quit",
    "help",
    # Common system commands
    "ls", "cd", "pwd", "cat", "echo", "grep", "find",
    "mkdir", "rm", "cp", "mv", "touch", "head", "tail",
    "python3", "pip3", "bash", "sh", "git", "curl", "wget",
    "ps", "kill", "top", "df", "du", "free", "uname",
]


def _get_plugin_names() -> list:
    try:
        from plugins.plugin_manager import get_plugin_manager
        return [p["name"] for p in get_plugin_manager().list_installed()]
    except Exception:
        return []


class ArrowCompleter:
    def __init__(self):
        self._matches = []
        self._setup_readline()

    def _setup_readline(self):
        readline.set_completer(self.complete)
        readline.set_completer_delims(" \t\n;|&")
        if "libedit" in (readline.__doc__ or ""):
            # macOS libedit compatibility
            readline.parse_and_bind("bind ^I rl_complete")
        else:
            readline.parse_and_bind("tab: complete")

    def complete(self, text: str, state: int) -> str:
        if state == 0:
            self._matches = self._get_matches(text)
        try:
            return self._matches[state]
        except IndexError:
            return None

    def _get_matches(self, text: str) -> list:
        buf = readline.get_line_buffer()
        tokens = buf.lstrip().split()

        # If no tokens yet or just one partial token: complete from builtins
        if not tokens or (len(tokens) == 1 and not buf.endswith(" ")):
            return [c + " " for c in BUILTIN_COMMANDS if c.startswith(text)]

        cmd = tokens[0].lower()

        # aios subcommand
        if cmd == "aios":
            subs = ["install", "remove", "list", "enable", "disable", "status", "update"]
            if len(tokens) == 1 or (len(tokens) == 2 and not buf.endswith(" ")):
                return [s + " " for s in subs if s.startswith(text)]
            # aios install/remove/enable/disable <plugin>
            if len(tokens) >= 2 and tokens[1] in ("install", "remove", "enable", "disable"):
                names = _get_plugin_names()
                return [n + " " for n in names if n.startswith(text)]

        # arrow build subcommand
        if cmd == "arrow":
            if len(tokens) >= 2 and tokens[1] == "build":
                types = ["service", "plugin", "layer"]
                if len(tokens) == 2 or (len(tokens) == 3 and not buf.endswith(" ")):
                    return [t + " " for t in types if t.startswith(text)]

        # Fall back to filesystem completion
        return self._path_complete(text)

    def _path_complete(self, text: str) -> list:
        """Complete file/directory paths."""
        if not text:
            path = "."
            prefix = ""
        else:
            path = os.path.dirname(text) or "."
            prefix = text

        try:
            entries = os.listdir(path)
        except OSError:
            return []

        matches = []
        for entry in entries:
            full = os.path.join(os.path.dirname(text), entry) if text else entry
            if full.startswith(prefix):
                if os.path.isdir(os.path.join(path, entry)):
                    matches.append(full + "/")
                else:
                    matches.append(full + " ")
        return sorted(matches)


def setup_history(history_file: str = None):
    """Load and configure readline command history."""
    if history_file is None:
        history_file = os.path.expanduser("~/.aios/arrow_history")

    history_dir = os.path.dirname(history_file)
    os.makedirs(history_dir, exist_ok=True)

    readline.set_history_length(1000)
    if os.path.isfile(history_file):
        try:
            readline.read_history_file(history_file)
        except Exception:
            pass
    return history_file


def save_history(history_file: str):
    try:
        readline.write_history_file(history_file)
    except Exception:
        pass
