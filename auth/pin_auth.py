"""
AIOS Auth — PIN Authentication
Stores a salted SHA-256 hash of the user's PIN.
On first launch: prompts to set a PIN.
Subsequent launches: validates PIN entry.
"""

import os
import sys
import json
import hashlib
import secrets
import getpass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

CFG_PATH = os.path.join(ROOT, "config", "aios.cfg")

from utils.colors import RESET, BOLD, CYAN, GREEN, RED, YELLOW, WHITE  # noqa: E402
from version import __version__ as _VERSION  # noqa: E402


def _load_cfg():
    try:
        with open(CFG_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}  # First run — expected
    except Exception as e:
        print(f"[auth] Warning: could not load config ({e})", file=sys.stderr)
        return {}


def _save_cfg(cfg):
    os.makedirs(os.path.dirname(CFG_PATH), exist_ok=True)
    try:
        with open(CFG_PATH, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"[auth] Error: could not save config ({e})", file=sys.stderr)
        raise


def _hash_pin(pin: str, salt: str) -> str:
    return hashlib.sha256((salt + pin).encode()).hexdigest()


def _draw_lock():
    print(f"\n  {CYAN}┌─────────────────────────────────────┐{RESET}")
    print(f"  {CYAN}│{RESET}  {BOLD}{WHITE}◈ AIOS  AUTHENTICATION REQUIRED{RESET}      {CYAN}│{RESET}")
    print(f"  {CYAN}│{RESET}  {CYAN}Autonomous Intelligence OS  v{_VERSION}{RESET}  {CYAN}│{RESET}")
    print(f"  {CYAN}└─────────────────────────────────────┘{RESET}\n")


class PinAuth:
    def __init__(self):
        self.cfg = _load_cfg()
        self.auth_cfg = self.cfg.get("auth", {})
        self.max_attempts = self.auth_cfg.get("max_attempts", 5)

    def _pin_is_set(self) -> bool:
        return bool(self.auth_cfg.get("pin_hash") and self.auth_cfg.get("pin_salt"))

    def _set_pin(self) -> bool:
        print(f"  {YELLOW}[AIOS] First boot — set your PIN to secure the system.{RESET}")
        print(f"  {YELLOW}       PIN can be 4–12 digits.{RESET}\n")
        for attempt in range(3):
            try:
                pin1 = getpass.getpass(f"  {CYAN}  Set PIN: {RESET}")
                if not pin1.isdigit() or not (4 <= len(pin1) <= 12):
                    print(f"  {RED}  PIN must be 4–12 digits only.{RESET}\n")
                    continue
                pin2 = getpass.getpass(f"  {CYAN}  Confirm PIN: {RESET}")
                if pin1 != pin2:
                    print(f"  {RED}  PINs do not match.{RESET}\n")
                    continue
                salt = secrets.token_hex(16)
                hashed = _hash_pin(pin1, salt)
                if "auth" not in self.cfg:
                    self.cfg["auth"] = {}
                self.cfg["auth"]["pin_hash"] = hashed
                self.cfg["auth"]["pin_salt"] = salt
                _save_cfg(self.cfg)
                print(f"\n  {GREEN}  PIN set successfully.{RESET}\n")
                return True
            except (KeyboardInterrupt, EOFError):
                print()
                return False
        print(f"  {RED}  Failed to set PIN after 3 attempts.{RESET}")
        return False

    def authenticate(self) -> bool:
        # If auth disabled in config
        if not self.auth_cfg.get("pin_required", True):
            return True

        _draw_lock()

        if not self._pin_is_set():
            if not self._set_pin():
                return False
            # Reload
            self.cfg = _load_cfg()
            self.auth_cfg = self.cfg.get("auth", {})

        stored_hash = self.auth_cfg.get("pin_hash", "")
        salt = self.auth_cfg.get("pin_salt", "")

        for attempt in range(1, self.max_attempts + 1):
            try:
                pin = getpass.getpass(f"  {CYAN}  Enter PIN: {RESET}")
            except (KeyboardInterrupt, EOFError):
                print()
                return False

            if _hash_pin(pin, salt) == stored_hash:
                print(f"\n  {GREEN}  ✓ Authentication successful.{RESET}\n")
                try:
                    from cc.events import get_event_bus, LEVEL_OK
                    get_event_bus().emit("auth", LEVEL_OK, "Authentication successful")
                except Exception:
                    pass
                return True

            remaining = self.max_attempts - attempt
            if remaining > 0:
                print(f"  {RED}  Incorrect PIN. {remaining} attempt(s) remaining.{RESET}\n")
                try:
                    from cc.events import get_event_bus, LEVEL_WARN
                    get_event_bus().emit("auth", LEVEL_WARN,
                                         f"Failed PIN attempt ({attempt}/{self.max_attempts})")
                except Exception:
                    pass
            else:
                print(f"  {RED}  Maximum attempts exceeded. System locked.{RESET}\n")
                try:
                    from cc.events import get_event_bus, LEVEL_ERROR
                    get_event_bus().emit("auth", LEVEL_ERROR, "Max PIN attempts exceeded — system locked")
                except Exception:
                    pass

        return False
