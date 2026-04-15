"""
AIOS ARROW Shell — Built-in AIOS Commands
These are dispatched before hitting the system shell.
"""

import os
import sys
import time
import json

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RESET  = "\033[0m"
BOLD   = "\033[1m"
CYAN   = "\033[1;36m"
GREEN  = "\033[1;32m"
RED    = "\033[1;31m"
YELLOW = "\033[1;33m"
BLUE   = "\033[1;34m"
WHITE  = "\033[1;37m"
GRAY   = "\033[0;37m"
DIM    = "\033[2m"


def cmd_sysinfo(args: list) -> int:
    """Display real-time system information."""
    from kernel.kal import get_kal
    kal = get_kal()
    mem  = kal.get_memory()
    cpu  = kal.get_cpu_percent()
    disk = kal.get_disk_usage(ROOT)
    info = kal.get_platform_info()

    print(f"\n  {CYAN}{'─' * 50}{RESET}")
    print(f"  {BOLD}{WHITE}◈ AIOS SYSTEM INFORMATION{RESET}")
    print(f"  {CYAN}{'─' * 50}{RESET}")
    print(f"  {CYAN}Hostname   {RESET}: {info['hostname']}")
    print(f"  {CYAN}Platform   {RESET}: {info['system']} {info['release']} ({info['machine']})")
    print(f"  {CYAN}Python     {RESET}: {info['python']}")
    print(f"  {CYAN}KAL        {RESET}: Linux (Kernel Abstraction Layer v1.0.0)")
    print(f"  {CYAN}Uptime     {RESET}: {kal.get_uptime_str()}")
    print(f"  {CYAN}{'─' * 50}{RESET}")
    used_pct = mem['percent']
    bar_len  = 30
    filled   = int(bar_len * used_pct / 100)
    bar_color = RED if used_pct > 80 else (YELLOW if used_pct > 60 else GREEN)
    bar = bar_color + "█" * filled + GRAY + "░" * (bar_len - filled) + RESET
    print(f"  {CYAN}Memory     {RESET}: [{bar}] {used_pct}%")
    print(f"             {GRAY}{mem['used_mb']}MB used / {mem['total_mb']}MB total / {mem['available_mb']}MB free{RESET}")
    print(f"  {CYAN}CPU        {RESET}: {cpu}%")
    print(f"  {CYAN}Disk       {RESET}: {disk['used_mb']}MB used / {disk['total_mb']}MB total ({disk['percent']}% at {ROOT})")
    print(f"  {CYAN}{'─' * 50}{RESET}\n")
    return 0


def cmd_aios(args: list) -> int:
    """aios <subcommand> [args] — AIOS system management."""
    if not args:
        _aios_help()
        return 0

    sub = args[0].lower()
    rest = args[1:]

    if sub == "install":
        if not rest:
            print(f"  {RED}Usage: aios install <plugin-name>{RESET}")
            return 1
        from plugins.plugin_manager import get_plugin_manager
        pm = get_plugin_manager()
        ok, msg = pm.install(rest[0])
        color = GREEN if ok else RED
        print(f"  {color}{msg}{RESET}")
        return 0 if ok else 1

    elif sub == "remove":
        if not rest:
            print(f"  {RED}Usage: aios remove <plugin-name>{RESET}")
            return 1
        from plugins.plugin_manager import get_plugin_manager
        pm = get_plugin_manager()
        ok, msg = pm.remove(rest[0])
        color = GREEN if ok else RED
        print(f"  {color}{msg}{RESET}")
        return 0 if ok else 1

    elif sub == "list":
        from plugins.plugin_manager import get_plugin_manager
        pm = get_plugin_manager()
        what = rest[0] if rest else "installed"

        if what == "installed":
            installed = pm.list_installed()
            if not installed:
                print(f"  {GRAY}No plugins installed. Use 'aios install <name>' to add one.{RESET}")
                return 0
            print(f"\n  {CYAN}{'─' * 50}{RESET}")
            print(f"  {BOLD}INSTALLED PLUGINS{RESET}")
            print(f"  {CYAN}{'─' * 50}{RESET}")
            for p in installed:
                status = f"{GREEN}enabled{RESET}" if p["enabled"] else f"{RED}disabled{RESET}"
                print(f"  {WHITE}{p['name']:<20}{RESET} v{p['version']:<8} [{status}]")
                print(f"  {GRAY}  {p['description']}{RESET}")
            print(f"  {CYAN}{'─' * 50}{RESET}\n")

        elif what in ("available", "all", "plugins"):
            available = pm.list_available()
            print(f"\n  {CYAN}{'─' * 50}{RESET}")
            print(f"  {BOLD}AVAILABLE PLUGINS{RESET}")
            print(f"  {CYAN}{'─' * 50}{RESET}")
            for p in available:
                inst = f"{GREEN}[installed]{RESET}" if p.get("installed") else f"{GRAY}[not installed]{RESET}"
                print(f"  {WHITE}{p['name']:<20}{RESET} v{p.get('version','?'):<8} {inst}")
                print(f"  {GRAY}  {p.get('description','')}{RESET}")
            print(f"  {CYAN}{'─' * 50}{RESET}\n")
        return 0

    elif sub == "enable":
        if not rest:
            print(f"  {RED}Usage: aios enable <plugin-name>{RESET}")
            return 1
        from plugins.plugin_manager import get_plugin_manager
        ok, msg = get_plugin_manager().enable(rest[0])
        print(f"  {GREEN if ok else RED}{msg}{RESET}")
        return 0 if ok else 1

    elif sub == "disable":
        if not rest:
            print(f"  {RED}Usage: aios disable <plugin-name>{RESET}")
            return 1
        from plugins.plugin_manager import get_plugin_manager
        ok, msg = get_plugin_manager().disable(rest[0])
        print(f"  {GREEN if ok else RED}{msg}{RESET}")
        return 0 if ok else 1

    elif sub == "run":
        if not rest:
            print(f"  {RED}Usage: aios run <plugin-name> [args...]{RESET}")
            return 1
        return _cmd_plugin_run(rest[0], rest[1:])

    elif sub == "stop":
        if not rest:
            print(f"  {RED}Usage: aios stop <plugin-name>{RESET}")
            return 1
        return _cmd_plugin_stop(rest[0])

    elif sub == "status":
        cmd_sysinfo([])
        return 0

    elif sub == "update":
        print(f"  {CYAN}[AIOS] Checking for updates...{RESET}")
        from kernel.kal import get_kal
        result = get_kal().run_command(["git", "-C", ROOT, "pull"])
        if result["returncode"] == 0:
            print(f"  {GREEN}{result['stdout'].strip()}{RESET}")
        else:
            print(f"  {YELLOW}Could not pull updates: {result['stderr'].strip()}{RESET}")
        return result["returncode"]

    elif sub == "version":
        return _cmd_version()

    elif sub in ("help", "--help", "-h"):
        _aios_help()
        return 0

    else:
        print(f"  {RED}Unknown aios subcommand: '{sub}'. Try 'aios help'.{RESET}")
        return 1


def _cmd_plugin_run(name: str, plugin_args: list) -> int:
    """Run a plugin by name, forwarding args to plugin's main()."""
    import importlib.util
    import os as _os
    plug_dir = _os.path.join(ROOT, "plugins", "installed", name)
    entry    = _os.path.join(plug_dir, "main.py")
    if not _os.path.isfile(entry):
        print(f"  {RED}Plugin '{name}' not installed or missing main.py{RESET}")
        return 1
    try:
        spec = importlib.util.spec_from_file_location(f"plugin_{name}", entry)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        cmd_args = plugin_args or ["run"]
        if hasattr(mod, "main"):
            mod.main(cmd_args)
        else:
            print(f"  {RED}Plugin '{name}' has no main() entry point.{RESET}")
            return 1
        try:
            from cc.events import get_event_bus, LEVEL_INFO
            get_event_bus().emit("aios", LEVEL_INFO, f"Plugin run: {name} {' '.join(cmd_args)}")
        except Exception:
            pass
        return 0
    except Exception as e:
        print(f"  {RED}Error running plugin '{name}': {e}{RESET}")
        return 1


def _cmd_plugin_stop(name: str) -> int:
    """Send stop command to a running plugin."""
    return _cmd_plugin_run(name, ["stop"])


def _cmd_version() -> int:
    """Print all AIOS component versions."""
    versions = [
        ("AIOS",    "1.0.0"),
        ("KAL",     "1.0.0"),
        ("ARROW",   "1.0.0"),
        ("AURA",    "1.0.0"),
        ("AIM",     "1.0.0"),
        ("CC",      "1.0.0"),
    ]
    print(f"\n  {CYAN}{'─' * 40}{RESET}")
    print(f"  {BOLD}{WHITE}AIOS Component Versions{RESET}")
    print(f"  {CYAN}{'─' * 40}{RESET}")
    for component, ver in versions:
        print(f"  {CYAN}{component:<12}{RESET} v{ver}")
    try:
        import sys as _sys
        print(f"  {CYAN}{'Python':<12}{RESET} {_sys.version.split()[0]}")
    except Exception:
        pass
    print(f"  {CYAN}{'─' * 40}{RESET}\n")
    return 0


def _aios_help():
    print(f"""
  {CYAN}{'─' * 54}{RESET}
  {BOLD}AIOS COMMANDS{RESET}
  {CYAN}{'─' * 54}{RESET}
  {WHITE}aios install <plugin>{RESET}            Install a plugin
  {WHITE}aios remove  <plugin>{RESET}            Remove a plugin
  {WHITE}aios list [installed|available]{RESET}  List plugins
  {WHITE}aios enable  <plugin>{RESET}            Enable a plugin
  {WHITE}aios disable <plugin>{RESET}            Disable a plugin
  {WHITE}aios run     <plugin> [args]{RESET}     Run/start a plugin
  {WHITE}aios stop    <plugin>{RESET}            Stop a running plugin
  {WHITE}aios status{RESET}                      Show system status
  {WHITE}aios version{RESET}                     Print component versions
  {WHITE}aios update{RESET}                      Pull latest AIOS updates
  {CYAN}{'─' * 54}{RESET}
""")


def cmd_aura(args: list) -> int:
    """aura <query> — Ask AURA AI a question."""
    if not args:
        print(f"  {YELLOW}Usage: aura <your question>{RESET}")
        return 1
    from ai.aura import get_aura
    query = " ".join(args)
    aura = get_aura()
    response = aura.query(query)
    print(f"\n  {CYAN}◈ AURA:{RESET} {response}\n")
    return 0


def cmd_aim(args: list) -> int:
    """aim <subcommand> — AIM web bridge."""
    sub = args[0].lower() if args else "status"

    if sub == "status":
        from aim.aim import get_aim
        aim = get_aim()
        s = aim.get_status()
        online_str = f"{GREEN}ONLINE{RESET}" if s["online"] else f"{RED}OFFLINE{RESET}"
        print(f"\n  {CYAN}◈ AIM — Adaptive Interface Mesh{RESET}")
        print(f"  Status   : {online_str}")
        print(f"  Queued   : {s['queued']} request(s)")
        print(f"  Version  : {s['version']}")
        if s.get("gateway_port"):
            gw = f"{GREEN}running on :{s['gateway_port']}{RESET}"
            print(f"  Gateway  : {gw}")
        print()
        return 0

    elif sub == "check":
        from aim.aim import get_aim
        online = get_aim().check_now()
        print(f"  {GREEN if online else RED}{'Online' if online else 'Offline'}{RESET}")
        return 0

    elif sub == "fetch":
        if len(args) < 2:
            print(f"  {RED}Usage: aim fetch <url>{RESET}")
            return 1
        from aim.aim import get_aim
        result = get_aim().fetch(args[1])
        if result["ok"]:
            print(result["body"][:2000])
        else:
            print(f"  {RED}Error: {result['error']}{RESET}")
        return 0 if result["ok"] else 1

    elif sub == "serve":
        from aim.aim import get_aim
        aim  = get_aim()
        port = int(args[1]) if len(args) > 1 else None
        ok, msg = aim.start_gateway(port)
        print(f"  {GREEN if ok else RED}{msg}{RESET}")
        return 0 if ok else 1

    elif sub == "stop":
        from aim.aim import get_aim
        aim = get_aim()
        aim.stop_gateway()
        print(f"  {GREEN}AIM gateway stopped.{RESET}")
        return 0

    else:
        print(f"  {CYAN}aim status{RESET}         — connectivity status")
        print(f"  {CYAN}aim check{RESET}          — force connectivity check")
        print(f"  {CYAN}aim fetch <url>{RESET}    — fetch URL via AIM")
        print(f"  {CYAN}aim serve [port]{RESET}   — start local HTTP gateway (default :7070)")
        print(f"  {CYAN}aim stop{RESET}           — stop local HTTP gateway")
        return 0


def cmd_services(args: list) -> int:
    """services — List running AIOS services."""
    from kernel.kal import get_kal
    kal = get_kal()
    procs = kal.list_processes()
    if not procs:
        print(f"  {GRAY}No AIOS-managed services running.{RESET}")
        return 0
    print(f"\n  {CYAN}{'─' * 50}{RESET}")
    print(f"  {BOLD}AIOS SERVICES{RESET}")
    print(f"  {CYAN}{'─' * 50}{RESET}")
    for p in procs:
        status_color = GREEN if p["status"] == "running" else RED
        print(f"  {WHITE}{p['name']:<20}{RESET} PID:{p['pid']:<8} "
              f"[{status_color}{p['status']}{RESET}]  started:{p['started_at']}")
    print(f"  {CYAN}{'─' * 50}{RESET}\n")
    return 0


def cmd_help(args: list) -> int:
    """Show ARROW shell help."""
    print(f"""
  {CYAN}╔══════════════════════════════════════════════════════╗{RESET}
  {CYAN}║  ARROW — Autonomous Routing Relay Orchestration     ║{RESET}
  {CYAN}║          Workflow Shell  v1.0.0                     ║{RESET}
  {CYAN}╚══════════════════════════════════════════════════════╝{RESET}

  {BOLD}BUILT-IN COMMANDS{RESET}
  {WHITE}sysinfo{RESET}                      System status and resource usage
  {WHITE}aios <sub> [args]{RESET}            AIOS management (install/remove/list/run/stop...)
  {WHITE}aura <query>{RESET}                 Ask AURA AI
  {WHITE}aim  <sub>{RESET}                   AIM web bridge (status/check/fetch/serve/stop)
  {WHITE}services{RESET}                     List AIOS-managed services
  {WHITE}arrow build service <name>{RESET}   Scaffold a new service
  {WHITE}arrow build plugin  <name>{RESET}   Scaffold a new plugin
  {WHITE}arrow build layer   <name>{RESET}   Scaffold a new system layer
  {WHITE}arrow run <plugin> [args]{RESET}    Run a plugin (alias for aios run)
  {WHITE}cc{RESET}                           Return to Command Center
  {WHITE}clear{RESET}                        Clear screen
  {WHITE}help{RESET}                         This message
  {WHITE}exit / quit{RESET}                  Exit ARROW shell

  {BOLD}PLUGINS{RESET}
  {WHITE}aios list available{RESET}          See all available plugins
  {WHITE}aios install <name>{RESET}          Install a plugin
  {WHITE}aios run <name> [cmd]{RESET}        Run a plugin command (start/stop/status/run...)

  {BOLD}SYSTEM COMMANDS{RESET}
  All standard Linux/Termux commands pass through to the system.
  Pipes (|), redirects (>, >>), and background (&) are supported.

  {BOLD}HISTORY & COMPLETION{RESET}
  ↑/↓ arrow keys — command history
  Tab            — auto-complete commands and paths
  Ctrl+R         — reverse history search (readline built-in)
  Ctrl+C         — cancel current input
""")
    return 0
