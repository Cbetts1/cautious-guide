"""CC Panel: Help."""


class HelpPanel:
    TITLE = "HELP"

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

        addline("  AIOS — Autonomous Intelligence Operating System",
                c.color_pair(3) | c.A_BOLD)
        addline("  v1.0.0  |  KAL: Linux Abstraction Layer")
        addline("")

        addline("  COMMAND CENTER NAVIGATION", c.A_BOLD)
        addline("  ↑ / ↓        Move between menu sections")
        addline("  Enter        Select / activate")
        addline("  Q            Quit AIOS")
        addline("")

        addline("  COMPONENTS", c.A_BOLD)
        addline("  AIOS     Autonomous Intelligence Operating System")
        addline("  ARROW    Autonomous Routing Relay Orchestration Workflow")
        addline("           Full shell: AIOS cmds + all Linux/Termux cmds")
        addline("  AURA     Autonomous Universal Reasoning Assistant")
        addline("           AI engine, rule-based now, LLM-ready")
        addline("  AIM      Adaptive Interface Mesh")
        addline("           Web bridge: online gateway / offline queue")
        addline("  KAL      Kernel Abstraction Layer")
        addline("           All OS calls go through KAL — swap-ready")
        addline("")

        addline("  QUICK COMMANDS (in ARROW shell)", c.A_BOLD)
        addline("  sysinfo                    Real-time system stats")
        addline("  aios install <plugin>      Install a plugin")
        addline("  aios list available        See all available plugins")
        addline("  aura <question>            Ask AURA AI")
        addline("  aim status                 AIM web bridge status")
        addline("  arrow build service <n>    Scaffold a new service")
        addline("  arrow build plugin  <n>    Build + install a plugin")
        addline("  arrow build layer   <n>    Create a new system layer")
        addline("")

        addline("  ARCHITECTURE", c.A_BOLD)
        addline("  Boot → KAL → CC → ARROW Shell → Services/Plugins")
        addline("  Plugins = pluggable .py modules in plugins/installed/")
        addline("  To swap kernel: replace kernel/kal.py only")
        addline("")

        addline("  Repository: github.com/Cbetts1/cautious-guide")
