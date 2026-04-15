"""
Tests for kernel/kal.py and kernel/memory.py.
"""
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from kernel.kal import KAL, get_kal
from kernel.memory import read_meminfo, read_cpu_percent
from kernel.process import ProcessRegistry


# ── KAL metadata ─────────────────────────────────────────────────────────────

def test_kal_version():
    kal = KAL()
    assert kal.get_version() == "1.0.0"


def test_kal_kernel_name():
    kal = KAL()
    assert kal.get_kernel_name() == "Linux"


def test_kal_hostname():
    kal = KAL()
    h = kal.get_hostname()
    assert isinstance(h, str) and len(h) > 0


def test_kal_platform_info_keys():
    kal = KAL()
    info = kal.get_platform_info()
    for key in ("system", "release", "machine", "python", "hostname"):
        assert key in info


# ── KAL uptime ────────────────────────────────────────────────────────────────

def test_kal_uptime_positive():
    kal = KAL()
    secs = kal.get_uptime_seconds()
    assert secs > 0


def test_kal_uptime_str_format():
    kal = KAL()
    s = kal.get_uptime_str()
    # Expected format: Nd Nh Nm Ns
    assert "d" in s and "h" in s and "m" in s and "s" in s


# ── Memory ────────────────────────────────────────────────────────────────────

def test_read_meminfo_keys():
    info = read_meminfo()
    for key in ("total_mb", "available_mb", "used_mb", "percent"):
        assert key in info


def test_read_meminfo_values_non_negative():
    info = read_meminfo()
    for key in ("total_mb", "available_mb", "used_mb", "percent"):
        assert info[key] >= 0


def test_kal_get_memory():
    kal = KAL()
    mem = kal.get_memory()
    assert mem["percent"] >= 0.0
    assert mem["percent"] <= 100.0


# ── CPU ───────────────────────────────────────────────────────────────────────

def test_read_cpu_returns_float():
    pct = read_cpu_percent(interval=0.05)
    assert isinstance(pct, float)
    assert 0.0 <= pct <= 100.0


def test_kal_get_cpu_percent():
    kal = KAL()
    pct = kal.get_cpu_percent()
    assert 0.0 <= pct <= 100.0


# ── Disk ──────────────────────────────────────────────────────────────────────

def test_kal_disk_usage_root():
    kal = KAL()
    disk = kal.get_disk_usage("/")
    for key in ("total_mb", "used_mb", "free_mb", "percent"):
        assert key in disk
    assert disk["total_mb"] >= 0
    assert disk["percent"] <= 100.0


def test_kal_disk_usage_bad_path():
    kal = KAL()
    disk = kal.get_disk_usage("/nonexistent/path")
    assert disk["total_mb"] == 0


# ── ProcessRegistry ───────────────────────────────────────────────────────────

def test_process_registry_register_and_list():
    reg = ProcessRegistry()
    reg.register("test-svc", os.getpid(), "test service")
    items = reg.list()
    names = [i["name"] for i in items]
    assert "test-svc" in names


def test_process_registry_unregister():
    reg = ProcessRegistry()
    reg.register("temp-svc", os.getpid(), "temp")
    reg.unregister("temp-svc")
    names = [i["name"] for i in reg.list()]
    assert "temp-svc" not in names


def test_process_registry_running_count():
    reg = ProcessRegistry()
    reg.register("alive-svc", os.getpid(), "alive")
    assert reg.running_count() >= 1


def test_process_registry_is_alive():
    reg = ProcessRegistry()
    reg.register("my-proc", os.getpid(), "check")
    entry = reg.get("my-proc")
    assert entry is not None
    assert entry.is_alive()


# ── KAL command execution ────────────────────────────────────────────────────

def test_kal_run_command_echo():
    kal = KAL()
    result = kal.run_command(["echo", "hello"])
    assert result["returncode"] == 0
    assert "hello" in result["stdout"]


def test_kal_run_command_missing():
    kal = KAL()
    result = kal.run_command(["__nonexistent_cmd__"])
    assert result["returncode"] == 127


def test_kal_run_shell():
    kal = KAL()
    result = kal.run_shell("echo aios-test")
    assert result["returncode"] == 0
    assert "aios-test" in result["stdout"]


# ── Singleton (thread-safe) ───────────────────────────────────────────────────

def test_get_kal_singleton():
    from kernel import kal as kal_mod
    # Reset singleton so we test fresh creation
    kal_mod._kal_instance = None
    kal_mod._kal_lock = __import__("threading").Lock()
    a = get_kal()
    b = get_kal()
    assert a is b
    # Restore the singleton to avoid interfering with other tests
