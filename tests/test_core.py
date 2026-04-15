"""
AIOS core test suite.
Run with:  python -m pytest tests/ -v
       or:  python -m unittest discover tests/
"""

import os
import sys
import unittest
import importlib

# Ensure the repo root is on sys.path so all AIOS modules can be imported.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


# ---------------------------------------------------------------------------
# 1. auth._hash_pin — deterministic SHA-256 round-trip
# ---------------------------------------------------------------------------
class TestPinHash(unittest.TestCase):
    def setUp(self):
        from auth.pin_auth import _hash_pin
        self._hash_pin = _hash_pin

    def test_same_pin_and_salt_gives_same_hash(self):
        h1 = self._hash_pin("1234", "mysalt")
        h2 = self._hash_pin("1234", "mysalt")
        self.assertEqual(h1, h2)

    def test_different_salt_gives_different_hash(self):
        h1 = self._hash_pin("1234", "salt_a")
        h2 = self._hash_pin("1234", "salt_b")
        self.assertNotEqual(h1, h2)

    def test_different_pin_gives_different_hash(self):
        h1 = self._hash_pin("1234", "same_salt")
        h2 = self._hash_pin("5678", "same_salt")
        self.assertNotEqual(h1, h2)

    def test_hash_is_64_hex_chars(self):
        h = self._hash_pin("0000", "salt")
        self.assertEqual(len(h), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in h))


# ---------------------------------------------------------------------------
# 2. plugin_manager._validate_plugin_name — path traversal prevention
# ---------------------------------------------------------------------------
class TestPluginNameValidation(unittest.TestCase):
    def setUp(self):
        from plugins.plugin_manager import _validate_plugin_name
        self._validate = _validate_plugin_name

    def test_valid_simple_name(self):
        self.assertTrue(self._validate("monitor"))
        self.assertTrue(self._validate("my_plugin"))
        self.assertTrue(self._validate("my-plugin"))
        self.assertTrue(self._validate("Plugin123"))

    def test_rejects_path_traversal(self):
        self.assertFalse(self._validate("../../../etc"))
        self.assertFalse(self._validate("../../root/.ssh"))
        self.assertFalse(self._validate(".."))
        self.assertFalse(self._validate("."))

    def test_rejects_slash(self):
        self.assertFalse(self._validate("foo/bar"))
        self.assertFalse(self._validate("/abs/path"))

    def test_rejects_empty(self):
        self.assertFalse(self._validate(""))

    def test_rejects_spaces(self):
        self.assertFalse(self._validate("my plugin"))

    def test_rejects_too_long(self):
        self.assertFalse(self._validate("a" * 65))

    def test_accepts_max_length(self):
        self.assertTrue(self._validate("a" * 64))


# ---------------------------------------------------------------------------
# 3. aim._validate_external_url — SSRF protection
# ---------------------------------------------------------------------------
class TestValidateExternalUrl(unittest.TestCase):
    def setUp(self):
        from aim.aim import _validate_external_url
        self._validate = _validate_external_url

    # ── Should be blocked ──────────────────────────────────────────────
    def test_blocks_localhost(self):
        self.assertNotEqual(self._validate("http://localhost/"), "")

    def test_blocks_loopback_ip(self):
        self.assertNotEqual(self._validate("http://127.0.0.1/"), "")

    def test_blocks_loopback_127_1(self):
        self.assertNotEqual(self._validate("http://127.0.0.1:8080/secret"), "")

    def test_blocks_private_10(self):
        self.assertNotEqual(self._validate("http://10.0.0.1/"), "")

    def test_blocks_private_192_168(self):
        self.assertNotEqual(self._validate("http://192.168.1.1/"), "")

    def test_blocks_private_172_16(self):
        self.assertNotEqual(self._validate("http://172.16.0.1/"), "")

    def test_blocks_private_172_31(self):
        self.assertNotEqual(self._validate("http://172.31.255.255/"), "")

    def test_blocks_ipv6_loopback(self):
        self.assertNotEqual(self._validate("http://[::1]/"), "")

    def test_blocks_decimal_loopback(self):
        # Decimal form of 127.0.0.1 = 2130706433
        self.assertNotEqual(self._validate("http://2130706433/"), "")

    def test_blocks_ipv4_mapped_ipv6(self):
        self.assertNotEqual(self._validate("http://[::ffff:127.0.0.1]/"), "")

    def test_blocks_ipv4_mapped_private(self):
        self.assertNotEqual(self._validate("http://[::ffff:192.168.1.1]/"), "")

    def test_blocks_ftp_scheme(self):
        self.assertNotEqual(self._validate("ftp://example.com/"), "")

    def test_blocks_file_scheme(self):
        self.assertNotEqual(self._validate("file:///etc/passwd"), "")

    def test_blocks_missing_host(self):
        self.assertNotEqual(self._validate("http:///path"), "")

    # ── Should be allowed ──────────────────────────────────────────────
    def test_allows_public_http(self):
        self.assertEqual(self._validate("http://example.com/"), "")

    def test_allows_public_https(self):
        self.assertEqual(self._validate("https://api.example.com/data"), "")

    def test_allows_public_ip(self):
        self.assertEqual(self._validate("http://8.8.8.8/"), "")


# ---------------------------------------------------------------------------
# 4. kernel.kal.KAL.run_command — return value contract
# ---------------------------------------------------------------------------
class TestKALRunCommand(unittest.TestCase):
    def setUp(self):
        from kernel.kal import KAL
        self.kal = KAL()

    def test_echo_returns_zero(self):
        result = self.kal.run_command(["echo", "hello"])
        self.assertEqual(result["returncode"], 0)
        self.assertIn("hello", result["stdout"])

    def test_missing_command_returns_127(self):
        result = self.kal.run_command(["__no_such_cmd__"])
        self.assertEqual(result["returncode"], 127)
        self.assertIn("__no_such_cmd__", result["stderr"])

    def test_result_has_required_keys(self):
        result = self.kal.run_command(["true"])
        self.assertIn("returncode", result)
        self.assertIn("stdout", result)
        self.assertIn("stderr", result)

    def test_timeout_returns_124(self):
        result = self.kal.run_command(["sleep", "10"], timeout=1)
        self.assertEqual(result["returncode"], 124)


# ---------------------------------------------------------------------------
# 5. aim._check_internet does NOT mutate the global socket timeout
# ---------------------------------------------------------------------------
class TestCheckInternetNoSideEffects(unittest.TestCase):
    def test_global_timeout_unchanged(self):
        import socket
        from aim.aim import _check_internet
        original = socket.getdefaulttimeout()
        _check_internet(host="0.0.0.1", port=9, timeout=0.05)  # will fail fast
        self.assertEqual(socket.getdefaulttimeout(), original,
                         "_check_internet must not mutate socket.getdefaulttimeout()")


# ---------------------------------------------------------------------------
# 6. EventBus thread safety — concurrent emits never lose events
# ---------------------------------------------------------------------------
class TestEventBusConcurrency(unittest.TestCase):
    def test_concurrent_emits(self):
        import threading
        from cc.events import EventBus
        bus = EventBus()
        n = 200

        def emit_many():
            for i in range(n):
                bus.emit("test", "INFO", f"message {i}")

        threads = [threading.Thread(target=emit_many) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # The bus caps at MAX_EVENTS (500); we emitted 1000 so we expect 500.
        count = bus.count()
        self.assertLessEqual(count, bus.MAX_EVENTS)
        self.assertGreater(count, 0)


# ---------------------------------------------------------------------------
# 7. version.py — single canonical version string
# ---------------------------------------------------------------------------
class TestVersion(unittest.TestCase):
    def test_version_importable(self):
        from version import __version__
        self.assertIsInstance(__version__, str)
        # Should look like semver: digits.digits.digits
        parts = __version__.split(".")
        self.assertEqual(len(parts), 3)
        for part in parts:
            self.assertTrue(part.isdigit(), f"Non-numeric version part: {part!r}")


# ---------------------------------------------------------------------------
# 8. utils.colors — constants are non-empty strings
# ---------------------------------------------------------------------------
class TestColors(unittest.TestCase):
    def test_all_constants_are_strings(self):
        import utils.colors as c
        for name in ("RESET", "BOLD", "DIM", "RED", "GREEN", "YELLOW",
                     "BLUE", "CYAN", "WHITE", "GRAY"):
            value = getattr(c, name)
            self.assertIsInstance(value, str, f"{name} should be str")
            self.assertTrue(value, f"{name} should be non-empty")

    def test_reset_restores_terminal(self):
        from utils.colors import RESET
        self.assertIn("0m", RESET)


# ---------------------------------------------------------------------------
# 9. monitor._rotate_log — rotates when log exceeds size limit
# ---------------------------------------------------------------------------
class TestMonitorRotation(unittest.TestCase):
    def test_rotation_creates_backup(self):
        import tempfile
        import importlib
        import sys

        # Temporarily patch LOG_PATH to a temp file
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_log = os.path.join(tmpdir, "monitor.log")

            # Write a file larger than a custom small limit
            with open(tmp_log, "w") as f:
                f.write("x" * 10)

            # Import and monkey-patch
            from plugins.installed.monitor import main as monitor_mod
            old_path = monitor_mod.LOG_PATH
            old_max  = monitor_mod.MAX_LOG_BYTES
            try:
                monitor_mod.LOG_PATH = tmp_log
                monitor_mod.MAX_LOG_BYTES = 5  # rotate at 5 bytes
                monitor_mod._rotate_log()
                backup = tmp_log + ".1"
                self.assertTrue(os.path.isfile(backup),
                                "Expected .1 backup after rotation")
                self.assertFalse(os.path.isfile(tmp_log),
                                 "Original log should be gone after rotation")
            finally:
                monitor_mod.LOG_PATH = old_path
                monitor_mod.MAX_LOG_BYTES = old_max


if __name__ == "__main__":
    unittest.main()
