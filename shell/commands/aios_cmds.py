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

        elif what in ("available", "all"):
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

    elif sub in ("help", "--help", "-h"):
        _aios_help()
        return 0

    else:
        print(f"  {RED}Unknown aios subcommand: '{sub}'. Try 'aios help'.{RESET}")
        return 1


def _aios_help():
    print(f"""
  {CYAN}{'─' * 50}{RESET}
  {BOLD}AIOS COMMANDS{RESET}
  {CYAN}{'─' * 50}{RESET}
  {WHITE}aios install <plugin>{RESET}     Install a plugin
  {WHITE}aios remove  <plugin>{RESET}     Remove a plugin
  {WHITE}aios list [installed|available]{RESET}  List plugins
  {WHITE}aios enable  <plugin>{RESET}     Enable a plugin
  {WHITE}aios disable <plugin>{RESET}     Disable a plugin
  {WHITE}aios status{RESET}              Show system status
  {WHITE}aios update{RESET}              Pull latest AIOS updates
  {CYAN}{'─' * 50}{RESET}
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
        print(f"  Version  : {s['version']}\n")
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

    else:
        print(f"  {CYAN}aim status{RESET}       — connectivity status")
        print(f"  {CYAN}aim check{RESET}        — force connectivity check")
        print(f"  {CYAN}aim fetch <url>{RESET}  — fetch URL via AIM")
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
  {WHITE}aios <sub> [args]{RESET}            AIOS management (install/remove/list...)
  {WHITE}aura <query>{RESET}                 Ask AURA AI
  {WHITE}aim  <sub>{RESET}                   AIM web bridge (status/check/fetch)
  {WHITE}services{RESET}                     List AIOS-managed services
  {WHITE}arrow build service <name>{RESET}   Scaffold a new service
  {WHITE}arrow build plugin  <name>{RESET}   Scaffold a new plugin
  {WHITE}arrow build layer   <name>{RESET}   Scaffold a new system layer
  {WHITE}cc{RESET}                           Return to Command Center
  {WHITE}clear{RESET}                        Clear screen
  {WHITE}help{RESET}                         This message
  {WHITE}exit / quit{RESET}                  Exit ARROW shell

  {BOLD}SYSTEM COMMANDS{RESET}
  All standard Linux/Termux commands pass through to the system.
  Pipes (|), redirects (>, >>), and background (&) are supported.

  {BOLD}HISTORY & COMPLETION{RESET}
  ↑/↓ arrow keys — command history
  Tab            — auto-complete commands and paths
  Ctrl+R         — reverse history search
  Ctrl+C         — cancel current input
""")
    return 0
