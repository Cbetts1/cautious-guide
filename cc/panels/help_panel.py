"""CC Panel: Help — AIOS onboarding, navigation, and command reference."""


class HelpPanel:
    TITLE = "HELP"

    def render(self, win, y: int, x: int, height: int, width: int,
               kal=None, curses_mod=None):
        c   = curses_mod
        row = y

        def addline(text="", attr=0):
            nonlocal row
            if row < y + height - 1:
                try:
                    win.addnstr(row, x, str(text), max(1, width - 1), attr)
                except Exception:
                    pass
                row += 1

        addline("  AIOS — Autonomous Intelligence Operating System",
                c.color_pair(3) | c.A_BOLD)
        addline("  v1.0.0  ·  KAL · ARROW · AIM · AURA · CC")
        addline("")

        addline("  COMMAND CENTER NAVIGATION", c.A_BOLD)
        addline("  ↑ / ↓         Move between panels")
        addline("  1–9           Jump to panel by number")
        addline("  Enter         Select / activate / launch ARROW")
        addline("  Q             Quit AIOS")
        addline("")

        addline("  PANELS", c.A_BOLD)
        addline("  [1] ◈ Home         Live overview — health, layers, events")
        addline("  [2] System         CPU, RAM, disk, platform, uptime")
        addline("  [3] Layers         Layer manager — KAL, AIM, AURA, ARROW")
        addline("  [4] ARROW Shell    Full shell — all AIOS + Linux/Termux cmds")
        addline("  [5] Services       AIOS-managed service registry")
        addline("  [6] AI / AURA      AI assistant — ask questions interactively")
        addline("  [7] Network/AIM    Bridge status + connectivity control")
        addline("  [8] Events         Live event log — history of system activity")
        addline("  [9] Storage        Disk usage across all mounts")
        addline("  Builder            Scaffold services, plugins, layers")
        addline("  Settings           View AIOS configuration")
        addline("")

        addline("  CORE COMPONENTS", c.A_BOLD)
        addline("  AIOS   Autonomous Intelligence Operating System")
        addline("  ARROW  Shell: AIOS commands + all Linux/Termux pass-through")
        addline("  AURA   AI engine — rule-based now, LLM-ready (add model to cfg)")
        addline("  AIM    Web bridge — online gateway / offline request queue")
        addline("  KAL    Kernel Abstraction Layer — all OS calls routed through")
        addline("")

        addline("  TOP COMMANDS (in ARROW shell)", c.A_BOLD)
        addline("  sysinfo                     Real-time system stats")
        addline("  layers                      Show all AIOS layers + status")
        addline("  aura <question>             Ask AURA AI")
        addline("  aim status                  AIM bridge status")
        addline("  aim check                   Force connectivity check")
        addline("  aios install <plugin>       Install a plugin")
        addline("  aios list available         Browse available plugins")
        addline("  arrow build service <name>  Scaffold a new service")
        addline("  arrow build layer   <name>  Create a new system layer")
        addline("  cc                          Return here from ARROW")
        addline("")

        addline("  ARCHITECTURE", c.A_BOLD)
        addline("  Boot → KAL → CC → ARROW Shell → Layers/Services/Plugins")
        addline("  All root + Linux/Termux commands pass through ARROW unchanged.")
        addline("")

        addline("  Repository: github.com/Cbetts1/cautious-guide")
