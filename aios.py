#!/usr/bin/env python3
"""
AIOS — Autonomous Intelligence Operating System
Entry point. Runs: Boot → Auth → Command Center
"""

import sys
import os

# Ensure AIOS root is on path
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from boot.bootloader import Bootloader
from auth.pin_auth import PinAuth
from cc.command_center import CommandCenter


def main():
    # ── Boot ────────────────────────────────────────────────────────────
    bootloader = Bootloader()
    ok = bootloader.run()
    if not ok:
        print("\n\033[1;31m[AIOS] Critical boot failure — entering recovery shell.\033[0m")
        os.execvp("bash", ["bash"])
        sys.exit(1)

    # ── Auth ────────────────────────────────────────────────────────────
    auth = PinAuth()
    if not auth.authenticate():
        print("\n\033[1;31m[AIOS] Authentication failed. System locked.\033[0m")
        sys.exit(1)

    # ── Command Center ──────────────────────────────────────────────────
    cc = CommandCenter()
    cc.run()


if __name__ == "__main__":
    main()
