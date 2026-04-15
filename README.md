# AIOS — Autonomous Intelligence Operating System

> **AI-personalized assistant OS with Command Center, ARROW shell, AIM web bridge, and pluggable AI engine.**

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   AIOS  v1.0.0                          │
│                                                         │
│  ┌──────────┐   ┌────────────┐   ┌──────────────────┐  │
│  │  BOOT    │──▶│   AUTH     │──▶│ Command Center   │  │
│  │ (POST)   │   │ (PIN/SHA2) │   │  (curses TUI)    │  │
│  └──────────┘   └────────────┘   └────────┬─────────┘  │
│                                           │             │
│              ┌────────────────────────────┼──────────┐  │
│              │                            │          │  │
│         ┌────▼──────┐  ┌─────────┐  ┌────▼────┐     │  │
│         │  ARROW    │  │  AURA   │  │   AIM   │     │  │
│         │  (Shell)  │  │  (AI)   │  │  (Web)  │     │  │
│         └────┬──────┘  └────┬────┘  └────┬────┘     │  │
│              │              │             │           │  │
│         ┌────▼──────────────▼─────────────▼────────┐ │  │
│         │          KAL — Kernel Abstraction Layer  │ │  │
│         │   memory · cpu · disk · processes · net  │ │  │
│         └───────────────────────────────────────────┘ │  │
│                                                         │
│  Plugins: monitor · webserver · filebrowser · codepad · sshbridge │
└─────────────────────────────────────────────────────────┘
```

### Components

| Name | Acronym | Description |
|------|---------|-------------|
| **AIOS** | Autonomous Intelligence OS | Core system, entry point (`aios.py`) |
| **ARROW** | Autonomous Routing Relay Orchestration Workflow | Full-featured shell |
| **AURA** | Autonomous Universal Reasoning Assistant | Rule-based AI engine, LLM-ready |
| **AIM** | Adaptive Interface Mesh | Web bridge: gateway when online, queue offline |
| **KAL** | Kernel Abstraction Layer | All OS calls go through `kernel/kal.py` |
| **CC** | Command Center | Curses TUI with 10 panels |

---

## Installation

### Linux / Debian / Ubuntu

```bash
sudo apt update && sudo apt install -y python3 git
git clone https://github.com/Cbetts1/cautious-guide.git
cd cautious-guide
python3 aios.py
```

### Termux (Android)

```bash
pkg update && pkg install python git
git clone https://github.com/Cbetts1/cautious-guide.git
cd cautious-guide
python3 aios.py
```

Or use the one-command installer:

```bash
bash install.sh
```

> **No pip install required.** AIOS uses only Python standard library.

### First Run

1. AIOS runs a boot POST sequence (pass/fail checks)
2. On first launch you are prompted to set a PIN (4–12 digits)
3. The Command Center opens — navigate with **↑/↓** or number keys **1–0**
4. Press **Enter** on **ARROW Shell** (item 2) to drop to the shell
5. Type `help` for all commands. Type `cc` to return to Command Center.

---

## Command Reference (ARROW Shell)

```
sysinfo                      Real-time system stats (CPU/mem/disk)
aios install <plugin>        Install a plugin
aios remove  <plugin>        Remove a plugin
aios list    [installed|available]  List plugins
aios enable/disable <plugin> Enable or disable a plugin
aios run  <plugin> [cmd]     Run a plugin command
aios stop <plugin>           Stop a running plugin
aios version                 Print all component versions
aios update                  Pull latest AIOS updates from git
aura <question>              Ask AURA AI anything about AIOS
aim  status                  AIM connectivity status
aim  check                   Force connectivity check
aim  fetch <url>             Fetch a URL via AIM
aim  serve  [port]           Start local HTTP gateway (default :7070)
aim  stop                    Stop local HTTP gateway
services                     List running AIOS services
arrow build service <name>   Scaffold a new background service
arrow build plugin  <name>   Scaffold and install a new plugin
arrow build layer   <name>   Create a new top-level AIOS system layer
arrow run   <plugin> [args]  Run a plugin (alias for aios run)
cc                           Return to Command Center
clear                        Clear the screen
help                         Full command reference
exit / quit                  Exit ARROW shell
```

**Shell features:** pipes (`|`), redirects (`>`, `>>`), background (`&`), Ctrl+R history search, Tab completion.

---

## Command Center Panels

| Key | Panel | Description |
|-----|-------|-------------|
| 1 | System | Live CPU / memory / disk / uptime |
| 2 | ARROW Shell | Drop into the shell |
| 3 | Services | Running services (↑/↓ + S to stop) |
| 4 | AI / AURA | Chat with AURA AI |
| 5 | Network / AIM | Network interfaces + AIM status |
| 6 | Storage | Disk usage + AIOS dirs (C = clean cache) |
| 7 | Builder | ARROW build system reference |
| 8 | Settings | Live config editing (↑/↓ + Enter to edit) |
| 9 | Help | Quick reference |
| 0 | Events | Scrollable system event log |

---

## Plugins

Five bundled plugins, all in `plugins/installed/`:

| Plugin | Type | Description |
|--------|------|-------------|
| `monitor` | service | CPU/mem/disk sampling every 5s → `~/.aios/monitor.log`. **Auto-started** at boot. |
| `webserver` | service | HTTP file server (default port 8080) using Python's `http.server` |
| `filebrowser` | tool | Curses file browser (↑/↓ navigate, Enter open, V view, Q quit) |
| `codepad` | tool | Minimal curses text editor (Ctrl+S save, Ctrl+Q quit) |
| `sshbridge` | service | SSH tunnel manager (configure then `aios run sshbridge start`) |

```bash
# Install all bundled plugins (they are pre-installed in this repo)
aios list available

# Run a plugin
aios run monitor start
aios run webserver start 8080
aios run filebrowser run /path
aios run codepad run config/aios.cfg
aios run sshbridge status
```

---

## Build System

Generate new AIOS components from the ARROW shell:

```bash
arrow build service <name> [--desc "description"]
arrow build plugin  <name> [--desc "description"]
arrow build layer   <name> [--desc "description"]
```

- **service** → `services/<name>/service.py` + `service.json`
- **plugin**  → `plugins/installed/<name>/main.py` + `manifest.json`
- **layer**   → `<name>/<name>.py` + `layer.json`

---

## Configuration

All settings live in `config/aios.cfg` (JSON). Edit via:
- **Settings panel** in CC (key 8 → ↑/↓ → Enter to edit a field)
- Directly with `aios run codepad run config/aios.cfg`

Key settings:

```json
{
  "system":  { "name": "AIOS", "hostname": "aios-node" },
  "boot":    { "show_post": true, "post_delay": 0.04 },
  "auth":    { "pin_required": true, "max_attempts": 5 },
  "aura":    { "mode": "rule", "model_path": "", "context_size": 20 },
  "aim":     { "enabled": true, "bridge_port": 7070 },
  "services":{ "autostart": ["monitor", "aura"] }
}
```

---

## Extending AIOS

### Add a custom AI model (LLM)
1. Install `llama-cpp-python`: `pip3 install llama-cpp-python`
2. Download a GGUF model
3. Set `aura.model_path` in `config/aios.cfg` to the model file path
4. Set `aura.mode` to `"llm"`

### Swap the kernel
Replace `kernel/kal.py`. All interfaces remain the same — no other file changes needed.

### Write a plugin
```bash
arrow build plugin myplugin --desc "My custom plugin"
# Then edit: plugins/installed/myplugin/main.py
aios run myplugin
```

---

## Roadmap

- [ ] LLM integration (llama.cpp / Ollama)
- [ ] Web dashboard (AIM gateway UI)
- [ ] Plugin marketplace / remote registry
- [ ] Multi-user PIN profiles
- [ ] AURA voice interface
- [ ] AIOS package format (.aiosp)

---

## Repository

**GitHub:** https://github.com/Cbetts1/cautious-guide  
**License:** MIT
