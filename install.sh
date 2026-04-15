#!/usr/bin/env bash
# AIOS One-Command Installer for Termux (Android) and Linux
# Usage: bash install.sh

set -e

REPO_URL="https://github.com/Cbetts1/cautious-guide.git"
REPO_DIR="cautious-guide"

RESET="\033[0m"
BOLD="\033[1m"
CYAN="\033[1;36m"
GREEN="\033[1;32m"
RED="\033[1;31m"
YELLOW="\033[1;33m"

echo ""
echo -e "  ${CYAN}╔══════════════════════════════════════════════════════╗${RESET}"
echo -e "  ${CYAN}║  AIOS — Autonomous Intelligence Operating System    ║${RESET}"
echo -e "  ${CYAN}║          One-Command Installer  v1.0.0              ║${RESET}"
echo -e "  ${CYAN}╚══════════════════════════════════════════════════════╝${RESET}"
echo ""

# ── Detect environment ────────────────────────────────────────────────────────
if command -v pkg >/dev/null 2>&1; then
    ENV="termux"
    echo -e "  ${CYAN}[ INFO ]${RESET}  Environment: Termux (Android)"
elif command -v apt >/dev/null 2>&1; then
    ENV="debian"
    echo -e "  ${CYAN}[ INFO ]${RESET}  Environment: Debian/Ubuntu Linux"
else
    ENV="generic"
    echo -e "  ${YELLOW}[ WARN ]${RESET}  Unknown package manager — attempting generic install"
fi

# ── Install dependencies ──────────────────────────────────────────────────────
echo ""
echo -e "  ${CYAN}── Installing dependencies ───────────────────────────${RESET}"

if [ "$ENV" = "termux" ]; then
    pkg update -y
    pkg install -y python git
    echo -e "  ${GREEN}[  OK  ]${RESET}  python + git installed via pkg"

elif [ "$ENV" = "debian" ]; then
    if [ "$(id -u)" -ne 0 ]; then
        echo -e "  ${YELLOW}[ WARN ]${RESET}  Not running as root — using sudo"
        SUDO="sudo"
    else
        SUDO=""
    fi
    $SUDO apt update -q
    $SUDO apt install -y -q python3 git
    echo -e "  ${GREEN}[  OK  ]${RESET}  python3 + git installed via apt"
else
    echo -e "  ${YELLOW}[ WARN ]${RESET}  Please ensure python3 and git are installed."
fi

# ── Verify Python ─────────────────────────────────────────────────────────────
if command -v python3 >/dev/null 2>&1; then
    PY_VER=$(python3 --version 2>&1)
    echo -e "  ${GREEN}[  OK  ]${RESET}  ${PY_VER}"
else
    echo -e "  ${RED}[ FAIL ]${RESET}  python3 not found. Install manually and re-run."
    exit 1
fi

# ── Clone repository ──────────────────────────────────────────────────────────
echo ""
echo -e "  ${CYAN}── Cloning AIOS repository ───────────────────────────${RESET}"

if [ -d "$REPO_DIR" ]; then
    echo -e "  ${YELLOW}[ WARN ]${RESET}  Directory '$REPO_DIR' already exists — pulling latest..."
    cd "$REPO_DIR"
    git pull
    cd ..
else
    git clone "$REPO_URL" "$REPO_DIR"
    echo -e "  ${GREEN}[  OK  ]${RESET}  Cloned into ./${REPO_DIR}"
fi

# ── Termux storage permission ─────────────────────────────────────────────────
if [ "$ENV" = "termux" ]; then
    echo ""
    echo -e "  ${CYAN}── Termux Storage Setup ──────────────────────────────${RESET}"
    echo -e "  ${YELLOW}[ NOTE ]${RESET}  Run 'termux-setup-storage' if you need external storage access."
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "  ${CYAN}── Installation Complete ─────────────────────────────${RESET}"
echo ""
echo -e "  ${BOLD}To launch AIOS:${RESET}"
echo -e "    cd ${REPO_DIR} && python3 aios.py"
echo ""
echo -e "  ${CYAN}First run:${RESET} you will be prompted to set a PIN (4–12 digits)."
echo -e "  ${CYAN}Then:${RESET}      the Command Center opens. Press 2 for ARROW shell."
echo -e "  ${CYAN}Shell:${RESET}     type 'help' for all commands."
echo ""
echo -e "  ${GREEN}◈ AIOS ready — Autonomous Intelligence OS${RESET}"
echo ""
