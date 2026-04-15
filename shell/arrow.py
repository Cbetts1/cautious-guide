"""
AIOS ARROW Shell
Autonomous Routing Relay Orchestration Workflow

Full interactive shell supporting:
  - AIOS built-in commands
  - System / Termux pass-through commands
  - Pipes, redirects, background processes
  - Command history + tab completion
  - arrow build system
"""

import os
import sys
import subprocess
import shlex
import signal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from utils.ansi import RESET, BOLD, CYAN, GREEN, RED, WHITE, BLUE, GRAY

# ── Built-in dispatcher ───────────────────────────────────────────────────────

def _dispatch(cmd: str, args: list) -> tuple[bool, int]:
    """
    Try to handle cmd as a built-in AIOS command.
    Returns (handled, exit_code).
    """
    from shell.commands.aios_cmds import (
        cmd_sysinfo, cmd_aios, cmd_aura, cmd_aim, cmd_services, cmd_help
    )
    from shell.commands.build_cmds import cmd_arrow_build

    builtins = {
        "sysinfo":  cmd_sysinfo,
        "aios":     cmd_aios,
        "aura":     cmd_aura,
        "aim":      cmd_aim,
        "services": cmd_services,
        "help":     cmd_help,
    }

    if cmd in builtins:
        try:
            rc = builtins[cmd](args)
            return True, (rc if isinstance(rc, int) else 0)
        except Exception as e:
            print(f"  {RED}Error in {cmd}: {e}{RESET}")
            return True, 1

    if cmd == "arrow":
        if args and args[0] == "build":
            try:
                rc = cmd_arrow_build(args[1:])
                return True, (rc if isinstance(rc, int) else 0)
            except Exception as e:
                print(f"  {RED}Error in arrow build: {e}{RESET}")
                return True, 1
        elif args and args[0] == "run":
            # arrow run <plugin> [args...] — alias for aios run
            from shell.commands.aios_cmds import cmd_aios
            try:
                rc = cmd_aios(["run"] + args[1:])
                return True, (rc if isinstance(rc, int) else 0)
            except Exception as e:
                print(f"  {RED}Error in arrow run: {e}{RESET}")
                return True, 1
        else:
            print(f"  {CYAN}arrow build <service|plugin|layer> <name>{RESET}")
            print(f"  {CYAN}arrow run <plugin> [args]{RESET}")
            return True, 0

    return False, 0


# ── Shell prompt ──────────────────────────────────────────────────────────────

def _prompt() -> str:
    cwd = os.getcwd()
    home = os.path.expanduser("~")
    if cwd.startswith(home):
        cwd = "~" + cwd[len(home):]
    return f"{CYAN}◈ ARROW{RESET} {BLUE}{cwd}{RESET} {GREEN}▶{RESET} "


# ── Main shell loop ───────────────────────────────────────────────────────────

class Arrow:
    VERSION = _VERSION

    def __init__(self):
        self._running    = False
        self._last_rc    = 0
        self._history_file = None
        self._completer  = None

    def _setup(self):
        # History + completion
        try:
            from shell.completer import ArrowCompleter, setup_history, save_history
            self._completer = ArrowCompleter()
            self._history_file = setup_history()
            self._save_history = save_history
        except Exception:
            self._save_history = lambda _: None

        # Ignore Ctrl+C in the shell loop itself (pass to child processes)
        signal.signal(signal.SIGINT, signal.SIG_IGN)

    def _teardown(self):
        if self._history_file and hasattr(self, "_save_history"):
            self._save_history(self._history_file)
        # Restore default SIGINT
        signal.signal(signal.SIGINT, signal.SIG_DFL)

    def run(self):
        """Main interactive shell entry point."""
        self._running = True
        self._setup()
        self._print_banner()

        while self._running:
            try:
                line = input(_prompt())
            except EOFError:
                print()
                break
            except KeyboardInterrupt:
                print()
                continue

            line = line.strip()
            if not line:
                continue

            self._last_rc = self._execute(line)

        self._teardown()

    def _print_banner(self):
        print(f"\n  {CYAN}╔══════════════════════════════════════════════════════╗{RESET}")
        print(f"  {CYAN}║{RESET}  {BOLD}{WHITE}◈ ARROW  Autonomous Routing Relay Orchestration{RESET}  {CYAN}║{RESET}")
        print(f"  {CYAN}║{RESET}  {CYAN}      Workflow Shell  v{self.VERSION}{RESET}{'':>27}{CYAN}║{RESET}")
        print(f"  {CYAN}╚══════════════════════════════════════════════════════╝{RESET}")
        print(f"  {GRAY}Type 'help' for commands. Type 'cc' to return to Command Center.{RESET}\n")

    def _execute(self, line: str) -> int:
        """Parse and execute a command line."""
        # Handle exit/quit
        if line.lower() in ("exit", "quit"):
            self._running = False
            return 0

        # Return to CC
        if line.lower() == "cc":
            self._running = False
            return 0

        # Clear
        if line.lower() == "clear":
            os.system("clear")
            return 0

        # cd is a shell built-in, must handle here
        if line.startswith("cd ") or line == "cd":
            return self._builtin_cd(line)

        # Try to parse first token
        try:
            tokens = shlex.split(line)
        except ValueError as e:
            print(f"  {RED}Parse error: {e}{RESET}")
            return 1

        if not tokens:
            return 0

        cmd  = tokens[0].lower()
        args = tokens[1:]

        # Dispatch to AIOS built-ins
        handled, rc = _dispatch(cmd, args)
        if handled:
            return rc

        # Pass to system shell (supports pipes, redirects, &)
        return self._system(line)

    def _builtin_cd(self, line: str) -> int:
        """Handle cd command."""
        parts = line.split(None, 1)
        target = parts[1] if len(parts) > 1 else os.path.expanduser("~")
        target = os.path.expanduser(target)
        try:
            os.chdir(target)
            return 0
        except FileNotFoundError:
            print(f"  {RED}cd: no such directory: {target}{RESET}")
            return 1
        except PermissionError:
            print(f"  {RED}cd: permission denied: {target}{RESET}")
            return 1

    def _system(self, line: str) -> int:
        """
        Execute a system command via bash.
        Supports pipes, redirects, background (&).
        """
        try:
            result = subprocess.run(
                line,
                shell=True,
                executable="/bin/bash" if os.path.isfile("/bin/bash") else None,
            )
            return result.returncode
        except KeyboardInterrupt:
            print()
            return 130
        except Exception as e:
            print(f"  {RED}Execution error: {e}{RESET}")
            return 1

    def execute_command(self, line: str) -> int:
        """Execute a single command string non-interactively."""
        return self._execute(line.strip())


def main():
    """Entry point when ARROW is called directly."""
    shell = Arrow()
    # If arguments given, execute as a single command
    if len(sys.argv) > 1:
        cmd_line = " ".join(sys.argv[1:])
        rc = Arrow().execute_command(cmd_line)
        sys.exit(rc)
    else:
        shell.run()


if __name__ == "__main__":
    main()
