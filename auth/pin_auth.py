"""
AIOS Auth — PIN Authentication
Stores a salted PBKDF2-HMAC-SHA256 hash of the user's PIN in
~/.aios/auth.json (outside the project tree so it is never committed).

On first launch: prompts to set a PIN.
Subsequent launches: validates PIN entry.

Migration: if old SHA-256 credentials are detected in config/aios.cfg,
they are moved to ~/.aios/auth.json and removed from the config file.
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

CFG_PATH  = os.path.join(ROOT, "config", "aios.cfg")
AUTH_PATH = os.path.expanduser("~/.aios/auth.json")

# Hash algorithm version stored in auth file so future upgrades can detect old format
_HASH_VERSION = "pbkdf2-sha256-v1"

from utils.ansi import RESET, BOLD, CYAN, GREEN, RED, YELLOW, WHITE


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_cfg() -> dict:
    try:
        with open(CFG_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}  # First run — expected
    except Exception as e:
        print(f"[auth] Warning: could not load config ({e})", file=sys.stderr)
        return {}


def _save_cfg(cfg: dict):
    os.makedirs(os.path.dirname(CFG_PATH), exist_ok=True)
    try:
        with open(CFG_PATH, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"[auth] Error: could not save config ({e})", file=sys.stderr)
        raise


def _load_auth() -> dict:
    """Load auth credentials from ~/.aios/auth.json."""
    try:
        with open(AUTH_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_auth(auth: dict):
    """Persist auth credentials to ~/.aios/auth.json (never in project tree)."""
    os.makedirs(os.path.dirname(AUTH_PATH), exist_ok=True)
    with open(AUTH_PATH, "w") as f:
        json.dump(auth, f, indent=2)


def _hash_pin(pin: str, salt: str) -> str:
    """Derive a hash using PBKDF2-HMAC-SHA256 (100 000 iterations)."""
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        pin.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    )
    return dk.hex()


def _migrate_legacy_credentials(cfg: dict) -> bool:
    """
    If old SHA-256 credentials are present in config/aios.cfg, move them to
    ~/.aios/auth.json and strip them from the config.  Returns True if a
    migration was performed (caller should prompt user to reset PIN).
    """
    auth_section = cfg.get("auth", {})
    old_hash = auth_section.pop("pin_hash", None)
    old_salt = auth_section.pop("pin_salt", None)
    if old_hash and old_salt:
        # Save legacy credentials to the user-data file so they still work
        # but flag them as the old format so authenticate() detects them.
        auth_data = {
            "version":  "sha256-legacy",
            "pin_hash": old_hash,
            "pin_salt": old_salt,
        }
        _save_auth(auth_data)
        # Persist config without the credentials
        cfg["auth"] = auth_section
        _save_cfg(cfg)
        return True
    return False


def _draw_lock():
    from aios import AIOS_VERSION  # late import to avoid circular deps at module level
    print(f"\n  {CYAN}┌─────────────────────────────────────┐{RESET}")
    print(f"  {CYAN}│{RESET}  {BOLD}{WHITE}◈ AIOS  AUTHENTICATION REQUIRED{RESET}      {CYAN}│{RESET}")
    print(f"  {CYAN}│{RESET}  {CYAN}Autonomous Intelligence OS  v{AIOS_VERSION}{RESET}  {CYAN}│{RESET}")
    print(f"  {CYAN}└─────────────────────────────────────┘{RESET}\n")


# ── PinAuth ───────────────────────────────────────────────────────────────────

class PinAuth:
    def __init__(self):
        self.cfg      = _load_cfg()
        self.auth_cfg = self.cfg.get("auth", {})
        self.max_attempts = self.auth_cfg.get("max_attempts", 5)

        # Migrate legacy credentials on first instantiation
        _migrate_legacy_credentials(self.cfg)

        # Reload auth from user-data file
        self._auth_data = _load_auth()

    def _pin_is_set(self) -> bool:
        return bool(self._auth_data.get("pin_hash") and self._auth_data.get("pin_salt"))

    def _is_legacy_hash(self) -> bool:
        return self._auth_data.get("version", "") == "sha256-legacy"

    def _set_pin(self) -> bool:
        print(f"  {YELLOW}[AIOS] First boot — set your PIN to secure the system.{RESET}")
        print(f"  {YELLOW}       PIN can be 4–12 digits.{RESET}\n")
        for _attempt in range(3):
            try:
                pin1 = getpass.getpass(f"  {CYAN}  Set PIN: {RESET}")
                if not pin1.isdigit() or not (4 <= len(pin1) <= 12):
                    print(f"  {RED}  PIN must be 4–12 digits only.{RESET}\n")
                    continue
                pin2 = getpass.getpass(f"  {CYAN}  Confirm PIN: {RESET}")
                if pin1 != pin2:
                    print(f"  {RED}  PINs do not match.{RESET}\n")
                    continue
                salt   = secrets.token_hex(16)
                hashed = _hash_pin(pin1, salt)
                auth_data = {
                    "version":  _HASH_VERSION,
                    "pin_hash": hashed,
                    "pin_salt": salt,
                }
                _save_auth(auth_data)
                self._auth_data = auth_data
                print(f"\n  {GREEN}  PIN set successfully.{RESET}\n")
                return True
            except (KeyboardInterrupt, EOFError):
                print()
                return False
        print(f"  {RED}  Failed to set PIN after 3 attempts.{RESET}")
        return False

    def _verify_pin(self, pin: str) -> bool:
        """Verify a PIN against the stored credentials (any supported format)."""
        stored_hash = self._auth_data.get("pin_hash", "")
        salt        = self._auth_data.get("pin_salt", "")
        if self._is_legacy_hash():
            # Migration path: reproduce the old SHA-256 digest once to verify
            # the user's PIN, then immediately re-hash with pbkdf2_hmac.
            # This is the *only* place where the legacy algorithm is used and
            # it is intentional — we need the plaintext to upgrade.
            import hashlib as _hl
            candidate = _hl.sha256((salt + pin).encode()).hexdigest()  # nosec B324
            if candidate == stored_hash:
                # Upgrade to pbkdf2 now that we know the plaintext PIN
                new_salt   = secrets.token_hex(16)
                new_hash   = _hash_pin(pin, new_salt)
                auth_data  = {
                    "version":  _HASH_VERSION,
                    "pin_hash": new_hash,
                    "pin_salt": new_salt,
                }
                _save_auth(auth_data)
                self._auth_data = auth_data
                return True
            return False
        return _hash_pin(pin, salt) == stored_hash

    def authenticate(self) -> bool:
        # If auth disabled in config
        if not self.auth_cfg.get("pin_required", True):
            return True

        _draw_lock()

        if not self._pin_is_set():
            if not self._set_pin():
                return False
            self._auth_data = _load_auth()

        for attempt in range(1, self.max_attempts + 1):
            try:
                pin = getpass.getpass(f"  {CYAN}  Enter PIN: {RESET}")
            except (KeyboardInterrupt, EOFError):
                print()
                return False

            if self._verify_pin(pin):
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
                    get_event_bus().emit("auth", LEVEL_ERROR,
                                         "Max PIN attempts exceeded — system locked")
                except Exception:
                    pass

        return False
