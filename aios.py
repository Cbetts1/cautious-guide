#!/usr/bin/env python3
"""
AIOS — Autonomous Intelligence Operating System
Entry point. Runs: Boot → Auth → Command Center
"""

import sys
import os
import atexit
import signal

# Ensure AIOS root is on path
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Single source of truth for the AIOS version
AIOS_VERSION = "1.0.0"

from boot.bootloader import Bootloader
from auth.pin_auth import PinAuth
from cc.command_center import CommandCenter


def _graceful_shutdown(signum=None, frame=None):
    """Flush persistent state on SIGTERM or atexit."""
    try:
        from hub.hub_state import get_hub_state
        get_hub_state().save()
    except Exception:
        pass
    try:
        from projects.registry import get_registry
        get_registry().save()
    except Exception:
        pass


def main():
    # Register graceful-shutdown handlers
    atexit.register(_graceful_shutdown)
    signal.signal(signal.SIGTERM, _graceful_shutdown)

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
