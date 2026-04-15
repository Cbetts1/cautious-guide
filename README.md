# AIOS — Autonomous Intelligence Operating System

> **AI-personalized assistant OS with Studio Hub, Command Center, ARROW shell, AIM web bridge, and pluggable AI engine.**

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   AIOS  v1.0.0  — Studio Hub Edition            │
│                                                                 │
│  ┌──────────┐   ┌────────────┐   ┌──────────────────────────┐  │
│  │  BOOT    │──▶│   AUTH     │──▶│     Command Center       │  │
│  │ (POST)   │   │ (PIN/SHA2) │   │  Studio Hub / curses TUI │  │
│  └──────────┘   └────────────┘   └────────────┬─────────────┘  │
│                                               │                 │
│        ┌──────────────────────────────────────┼──────────────┐  │
│        │                                      │              │  │
│   ┌────▼──────┐  ┌─────────┐  ┌──────┐  ┌────▼────┐         │  │
│   │  ARROW    │  │  AURA   │  │ AIM  │  │   hub/  │         │  │
│   │  (Shell)  │  │  (AI)   │  │(Web) │  │projects/│         │  │
│   └────┬──────┘  └────┬────┘  └──────┘  │comms/   │         │  │
│        │              │                  │remote/  │         │  │
│   ┌────▼──────────────▼──────────────────▼────────────────┐  │  │
│   │              KAL — Kernel Abstraction Layer            │  │  │
│   │     memory · cpu · disk · processes · network         │  │  │
│   └───────────────────────────────────────────────────────┘  │  │
│                                                               │  │
│  Plugins: monitor · webserver · filebrowser · codepad · sshbridge │
└─────────────────────────────────────────────────────────────────┘
```

### Core Components

| Name | Acronym | Description |
|------|---------|-------------|
| **AIOS** | Autonomous Intelligence OS | Core system, entry point (`aios.py`) |
| **ARROW** | Autonomous Routing Relay Orchestration Workflow | Full-featured shell |
| **AURA** | Autonomous Universal Reasoning Assistant | Rule-based AI engine, LLM-ready |
| **AIM** | Adaptive Interface Mesh | Web bridge: gateway when online, queue offline |
| **KAL** | Kernel Abstraction Layer | All OS calls go through `kernel/kal.py` |
| **CC** | Command Center | Curses TUI with Studio Hub and all panels |

### Studio Hub Modules (new)

| Module | Path | Description |
|--------|------|-------------|
| Device Profile | `hub/device_profile.py` | Auto-detects device capability; Lite/Balanced/Full modes |
| Hub State | `hub/hub_state.py` | Session persistence: last panel, project, notifications |
| Project Registry | `projects/registry.py` | Metadata store for all AIOS projects |
| Comms Layer | `comms/base.py` | Provider-agnostic messaging, calling, and contacts |
| Remote Layer | `remote/base.py` | Provider-agnostic remote host control |
| Providers | `providers/base.py` | Base interfaces for swappable backend providers |

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
3. The Command Center opens on the **Studio Hub** panel
4. Navigate with **↑/↓** or number keys **1–0**
5. Press **Enter** on **ARROW Shell** (key 2) to drop to the shell
6. Type `help` for all commands. Type `cc` to return to Command Center.

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
| 1 | Studio Hub | Dashboard: stats, last project, comms/remote summary, quick actions |
| 2 | ARROW Shell | Drop into the ARROW shell |
| 3 | System | Live CPU / memory / disk / uptime |
| 4 | Services | Running services (↑/↓ + S to stop) |
| 5 | AI / AURA | Chat with AURA AI |
| 6 | Network / AIM | Network interfaces + AIM status |
| 7 | Storage | Disk usage + AIOS dirs (C = clean cache) |
| 8 | Builder | ARROW build system reference |
| 9 | Settings | Live config editing (↑/↓ + Enter to edit) |
| 0 | Events | Scrollable system event log |
| ↓ | Projects | Create and manage AIOS projects |
| ↓ | Messages | Communications: inbox, calls, contacts, providers |
| ↓ | Remote | Remote host control: connect, deploy, monitor |
| ↓ | Providers | View and manage backend providers |
| ↓ | Repair | System diagnostics and self-repair (press R to scan) |
| ↓ | Help | Quick reference for all panels and commands |

Navigate to panels beyond key 0 with **↑/↓** arrows.

---

## Studio Hub Features

### Device-aware performance modes

AIOS automatically detects device capability at startup:

| Mode | RAM / CPUs | Refresh | Use case |
|------|-----------|---------|----------|
| **Lite** | < 512 MB or ≤ 1 CPU | 5s | Low-spec phones, battery saving |
| **Balanced** | < 2 GB or ≤ 2 CPU | 2s | Mid-range phones (default) |
| **Full** | ≥ 2 GB and > 2 CPU | 1s | Desktop / high-spec devices |

Override the mode in `config/aios.cfg`:
```json
{ "hub": { "device_mode": "lite" } }
```

### Project registry

The project registry stores metadata for AIOS projects at `~/.aios/projects.json`.

Project types: `ai`, `os`, `vm`, `server`, `website`, `cloud`, `remote_agent`, `plugin`, `service`, `other`.

Use the **Projects** panel (navigate with ↓ past key 0) or the API:

```python
from projects.registry import get_registry
reg = get_registry()
pid = reg.create("My AI assistant", "ai")
reg.update(pid, status="running")
```

### Communications layer (skeleton)

The comms layer provides a provider-agnostic API for messaging and calls:

```python
from comms.base import get_comms_manager
from providers.base import MessagingProvider, get_provider_registry

class MyProvider(MessagingProvider):
    name = "my-sms"
    def connect(self):    return True
    def is_connected(self): return True
    def send_text(self, to, body): ...   # implement

p = MyProvider()
get_provider_registry().register(p)
get_comms_manager().register_provider(p)
```

### Remote control layer (skeleton)

```python
from remote.base import get_remote_manager
rm = get_remote_manager()
rm.add_host("my-vps", "192.168.1.10", port=22, provider_name="my-ssh")
result = rm.connect("my-vps")
result = rm.run_command("my-vps", "uptime")
```

### Provider abstraction

Swap backend providers without changing any UI code. Implement `BaseProvider`,
`MessagingProvider`, `VoiceProvider`, or `RemoteProvider` from `providers/base.py`.

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
aios list available
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
- **Settings panel** in CC (key 9 → ↑/↓ → Enter to edit a field)
- Directly with `aios run codepad run config/aios.cfg`

Key settings:

```json
{
  "system":  { "name": "AIOS", "hostname": "aios-node" },
  "boot":    { "show_post": true, "post_delay": 0.04 },
  "auth":    { "pin_required": true, "max_attempts": 5 },
  "aura":    { "mode": "rule", "model_path": "", "context_size": 20 },
  "aim":     { "enabled": true, "bridge_port": 7070 },
  "services":{ "autostart": ["monitor", "aura"] },
  "hub":     { "device_mode": "balanced" }
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

### Add a provider
Subclass `MessagingProvider`, `VoiceProvider`, or `RemoteProvider` from `providers/base.py`
and register it with the appropriate manager.

---

## Repair / Diagnostics

Open the **Repair** panel (navigate down from key 0), then press **R** to run a full
diagnostic scan. The scan checks:

- Python version, config file, data directories
- KAL kernel, AURA AI, AIM bridge, ARROW shell
- Plugin directory, EventBus, all Studio Hub modules

Failed checks are shown in red with an explanation; warnings in yellow; passing in green.
All results are also emitted to the EventBus (panel key 0).

---

## Roadmap

- [x] Studio Hub dashboard
- [x] Device-aware performance modes (Lite / Balanced / Full)
- [x] Per-panel error isolation and visible logging
- [x] Session persistence (last panel, last project)
- [x] Project registry (AI / OS / VM / server / website / cloud / agent)
- [x] Communications layer skeleton (messaging, calls, contacts, providers)
- [x] Remote control layer skeleton (hosts, connect/disconnect, deploy)
- [x] Provider abstraction (messaging, voice, remote)
- [x] Repair / diagnostics panel
- [ ] LLM integration (llama.cpp / Ollama)
- [ ] Web dashboard (AIM gateway UI)
- [ ] Plugin marketplace / remote registry
- [ ] Multi-user PIN profiles
- [ ] AURA voice interface
- [ ] AIOS package format (.aiosp)
- [ ] Live messaging provider (SMS / VoIP)
- [ ] SSH remote control provider

---

## Repository

**GitHub:** https://github.com/Cbetts1/cautious-guide  
**License:** MIT
