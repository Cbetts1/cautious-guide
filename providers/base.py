"""
AIOS Provider Base
Abstract base classes for swappable backend providers.

A provider can implement any subset of these interfaces. Callers
should always check provider.supports('feature') before calling a
feature-specific method so that partial providers degrade gracefully.
"""

from abc import ABC
from typing import List, Dict, Optional


# ── Feature flags ─────────────────────────────────────────────────────────────

FEAT_MESSAGING = "messaging"
FEAT_VOICE     = "voice"
FEAT_CONTACTS  = "contacts"
FEAT_PRESENCE  = "presence"
FEAT_REMOTE    = "remote"
FEAT_DEPLOY    = "deploy"
FEAT_CLOUD     = "cloud"


class BaseProvider(ABC):
    """
    Minimal contract every provider must implement.
    Subclass this and override the methods you support.
    """

    #: Human-readable name shown in the Providers panel.
    name: str = "unnamed"

    #: Set of FEAT_* strings this provider actually supports.
    features: set = set()

    def supports(self, feature: str) -> bool:
        return feature in self.features

    def connect(self) -> bool:
        """Establish a connection / session. Returns True on success."""
        return False

    def disconnect(self):
        """Close the connection gracefully."""

    def is_connected(self) -> bool:
        return False

    def health_check(self) -> dict:
        """Return a dict with at least {'ok': bool, 'message': str}."""
        return {"ok": False, "message": "not implemented"}

    def __repr__(self) -> str:
        return f"<Provider name={self.name!r} features={self.features}>"


class MessagingProvider(BaseProvider):
    """Provider that supports text messaging."""

    features = {FEAT_MESSAGING}

    def send_text(self, recipient: str, body: str) -> bool:
        """Send a text message. Returns True on success."""
        return False

    def get_messages(self, limit: int = 20) -> List[Dict]:
        """Return recent messages as list of dicts."""
        return []

    def get_contacts(self) -> List[Dict]:
        return []


class VoiceProvider(BaseProvider):
    """Provider that supports voice/calls."""

    features = {FEAT_VOICE}

    def start_call(self, target: str) -> bool:
        return False

    def end_call(self) -> bool:
        return False

    def is_in_call(self) -> bool:
        return False


class RemoteProvider(BaseProvider):
    """Provider for remote system control."""

    features = {FEAT_REMOTE}

    def run_command(self, cmd: str) -> dict:
        """Run a command on the remote. Returns {ok, stdout, stderr}."""
        return {"ok": False, "stdout": "", "stderr": "not connected"}

    def push_file(self, local_path: str, remote_path: str) -> bool:
        return False

    def pull_file(self, remote_path: str, local_path: str) -> bool:
        return False

    def service_status(self, service: str) -> dict:
        return {"ok": False, "status": "unknown"}


# ── Registry ───────────────────────────────────────────────────────────────────

class ProviderRegistry:
    """Simple in-process registry for registered providers."""

    def __init__(self):
        self._providers: Dict[str, BaseProvider] = {}

    def register(self, provider: BaseProvider):
        self._providers[provider.name] = provider

    def get(self, name: str) -> Optional[BaseProvider]:
        return self._providers.get(name)

    def list_all(self) -> List[BaseProvider]:
        return list(self._providers.values())

    def list_by_feature(self, feature: str) -> List[BaseProvider]:
        return [p for p in self._providers.values() if p.supports(feature)]

    def count(self) -> int:
        return len(self._providers)


_provider_registry_lock: __import__("threading").Lock = __import__("threading").Lock()
_provider_registry: ProviderRegistry = None


def get_provider_registry() -> ProviderRegistry:
    global _provider_registry
    if _provider_registry is None:
        with _provider_registry_lock:
            if _provider_registry is None:
                _provider_registry = ProviderRegistry()
    return _provider_registry
