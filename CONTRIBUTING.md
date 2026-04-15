# Contributing to AIOS

Thank you for your interest in improving AIOS! This document covers everything you need to get started as a contributor.

---

## Table of Contents

1. [Development Setup](#1-development-setup)
2. [Project Structure](#2-project-structure)
3. [Coding Conventions](#3-coding-conventions)
4. [Running Tests](#4-running-tests)
5. [Linting](#5-linting)
6. [Opening Issues](#6-opening-issues)
7. [Submitting Pull Requests](#7-submitting-pull-requests)
8. [Security Disclosures](#8-security-disclosures)

---

## 1. Development Setup

AIOS has **no third-party runtime dependencies** — it uses the Python standard library only.

```bash
# Clone the repo
git clone https://github.com/Cbetts1/cautious-guide.git
cd cautious-guide

# Python 3.8+ is required
python3 --version

# Optional: create a virtual env for dev tools only (linters, pytest)
python3 -m venv .venv
source .venv/bin/activate
pip install ruff pytest

# Run AIOS
python3 aios.py
```

> **Termux (Android):** `pkg update && pkg install python git` then follow the same steps above.

---

## 2. Project Structure

```
aios.py                 Entry point (Boot → Auth → CC)
boot/                   POST-style bootloader + service autostart
auth/                   PIN authentication (pbkdf2-hmac-sha256, credentials in ~/.aios/auth.json)
kernel/                 Kernel Abstraction Layer (KAL) — all OS calls go here
shell/                  ARROW interactive shell + built-in commands
ai/                     AURA rule-based AI engine (LLM-ready)
aim/                    AIM web bridge (online/offline, HTTP gateway)
cc/                     Command Center curses TUI + all panels
hub/                    Session state and device-profile detection
plugins/                Plugin manager + installed plugins
projects/               Project metadata registry
comms/                  Provider-agnostic communications layer
remote/                 Provider-agnostic remote-control layer
providers/              Abstract provider base classes
utils/                  Shared utilities (ANSI colours etc.)
config/                 aios.cfg (JSON config, no credentials)
tests/                  Pytest test suite
```

---

## 3. Coding Conventions

- **Python 3.8+** syntax only.
- **Standard library only** for runtime code. Dev-only dependencies (pytest, ruff) are fine.
- **ANSI colours:** always import from `utils.ansi` — never redeclare the constants locally.
- **Singletons:** use double-checked locking (`get_*()` factories with a module-level `threading.Lock`).
- **No secrets in source:** PIN credentials live in `~/.aios/auth.json`, never in `config/aios.cfg`.
- **Error handling:** catch broad exceptions only at resilience boundaries (TUI rendering, event callbacks). Pass `as e` and log to the EventBus (`cc.events`) where possible.
- **Version string:** a single `AIOS_VERSION` constant in `aios.py` — never hardcode elsewhere.

---

## 4. Running Tests

```bash
# From the repo root
python3 -m pytest tests/ -v
```

The test suite covers the KAL, PIN auth (including legacy migration), AURA rule matching, AIM URL validation, plugin manager CRUD, and the project registry.

---

## 5. Linting

```bash
# Run ruff on all Python files
ruff check .

# Auto-fix safe issues
ruff check --fix .
```

The CI workflow runs `ruff check` and `pytest` on every push and pull request.

---

## 6. Opening Issues

Please include:

- AIOS version (`aios version` in ARROW)
- Python version (`python3 --version`)
- OS / device (Linux, Termux, etc.)
- Steps to reproduce
- Expected vs. actual behaviour
- Boot output if the issue occurs at startup

---

## 7. Submitting Pull Requests

1. Fork the repo and create a feature branch: `git checkout -b my-feature`
2. Make your changes following the coding conventions above.
3. Add or update tests in `tests/` if you are changing behaviour.
4. Run `ruff check .` and `pytest tests/` locally and ensure both pass.
5. Open a PR against `main` with a clear description of what and why.
6. A maintainer will review and merge or request changes.

---

## 8. Security Disclosures

Please **do not** open a public issue for security vulnerabilities. Instead, open a [GitHub Security Advisory](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing/privately-reporting-a-security-vulnerability) so the maintainer can assess and patch before public disclosure.
