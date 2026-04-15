"""
AIOS Communications Base
Provider-agnostic interface for messaging, calling, and contacts.

This module provides the CommsManager that brokers all communication
features through registered providers. When no provider is configured,
all operations fail gracefully with clear error messages.
"""

import time
import threading
from typing import List, Dict, Optional

# ── Message model ──────────────────────────────────────────────────────────────

class Message:
    def __init__(self, sender: str, recipient: str, body: str,
                 provider: str = "", direction: str = "in"):
        self.sender    = sender
        self.recipient = recipient
        self.body      = body
        self.provider  = provider
        self.direction = direction          # "in" | "out"
        self.ts        = time.time()
        self.ts_str    = time.strftime("%H:%M:%S", time.localtime(self.ts))
        self.read      = direction == "out"

    def __repr__(self) -> str:
        arrow = "←" if self.direction == "in" else "→"
        return f"[{self.ts_str}] {arrow} {self.sender}: {self.body[:60]}"


# ── Contact model ──────────────────────────────────────────────────────────────

class Contact:
    def __init__(self, name: str, handle: str, provider: str = "",
                 status: str = "offline"):
        self.name     = name
        self.handle   = handle
        self.provider = provider
        self.status   = status    # online | offline | away | busy


# ── CommsManager ──────────────────────────────────────────────────────────────

class CommsManager:
    """
    Central manager for all communications.

    Routes send/receive operations through registered providers.
    Maintains an in-memory message log and contact list.
    Operations fail safely when no provider is connected.

    Usage::

        from comms.base import get_comms_manager
        cm = get_comms_manager()
        cm.send("alice", "Hello!")
        msgs = cm.get_messages()
    """

    MAX_MESSAGES = 200

    def __init__(self):
        self._lock     = threading.Lock()
        self._messages: List[Message] = []
        self._contacts: Dict[str, Contact] = {}
        self._providers = {}          # name → provider instance
        self._active_call: Optional[str] = None

    # ── Provider management ────────────────────────────────────────────

    def register_provider(self, provider) -> None:
        with self._lock:
            self._providers[provider.name] = provider

    def list_providers(self) -> list:
        with self._lock:
            return list(self._providers.values())

    def _messaging_provider(self):
        """Return first connected messaging provider, or None."""
        from providers.base import FEAT_MESSAGING
        with self._lock:
            providers = list(self._providers.values())
        for p in providers:
            if p.supports(FEAT_MESSAGING) and p.is_connected():
                return p
        return None

    def _voice_provider(self):
        from providers.base import FEAT_VOICE
        with self._lock:
            providers = list(self._providers.values())
        for p in providers:
            if p.supports(FEAT_VOICE) and p.is_connected():
                return p
        return None

    # ── Messaging ──────────────────────────────────────────────────────

    def send(self, recipient: str, body: str) -> dict:
        """
        Send a text message.
        Returns {ok: bool, message: str}
        """
        provider = self._messaging_provider()
        if provider is None:
            return {"ok": False,
                    "message": "No messaging provider connected. "
                               "Configure a provider in Settings → Providers."}
        ok = provider.send_text(recipient, body)
        if ok:
            msg = Message("me", recipient, body,
                          provider=provider.name, direction="out")
            self._append_message(msg)
            try:
                from cc.events import get_event_bus, LEVEL_INFO
                get_event_bus().emit("comms", LEVEL_INFO,
                                     f"Message sent to {recipient}")
            except Exception:
                pass
            return {"ok": True, "message": "Sent."}
        return {"ok": False, "message": "Provider send failed."}

    def receive(self, sender: str, body: str, provider_name: str = "") -> None:
        """Record an incoming message (called by provider callbacks)."""
        msg = Message(sender, "me", body,
                      provider=provider_name, direction="in")
        self._append_message(msg)
        try:
            from cc.events import get_event_bus, LEVEL_INFO
            get_event_bus().emit("comms", LEVEL_INFO,
                                 f"Message from {sender}")
            from hub.hub_state import get_hub_state
            get_hub_state().add_notification("messages")
        except Exception:
            pass

    def _append_message(self, msg: Message):
        with self._lock:
            self._messages.append(msg)
            if len(self._messages) > self.MAX_MESSAGES:
                self._messages = self._messages[-self.MAX_MESSAGES:]

    def get_messages(self, limit: int = 50) -> List[Message]:
        with self._lock:
            return list(self._messages[-limit:])

    def unread_count(self) -> int:
        with self._lock:
            return sum(1 for m in self._messages
                       if m.direction == "in" and not m.read)

    def mark_all_read(self):
        with self._lock:
            for m in self._messages:
                m.read = True

    # ── Calls ──────────────────────────────────────────────────────────

    def start_call(self, target: str) -> dict:
        provider = self._voice_provider()
        if provider is None:
            return {"ok": False,
                    "message": "No voice provider connected. "
                               "Configure a provider in Settings → Providers."}
        ok = provider.start_call(target)
        if ok:
            self._active_call = target
            try:
                from cc.events import get_event_bus, LEVEL_INFO
                get_event_bus().emit("comms", LEVEL_INFO,
                                     f"Call started: {target}")
            except Exception:
                pass
            return {"ok": True, "message": f"Calling {target}…"}
        return {"ok": False, "message": "Call failed to connect."}

    def end_call(self) -> dict:
        provider = self._voice_provider()
        if provider and self._active_call:
            provider.end_call()
        target = self._active_call
        self._active_call = None
        return {"ok": True, "message": f"Call ended: {target}"}

    def in_call(self) -> bool:
        return self._active_call is not None

    # ── Contacts ───────────────────────────────────────────────────────

    def add_contact(self, name: str, handle: str,
                    provider: str = "") -> Contact:
        c = Contact(name, handle, provider)
        with self._lock:
            self._contacts[handle] = c
        return c

    def get_contacts(self) -> List[Contact]:
        with self._lock:
            return list(self._contacts.values())

    def contact_count(self) -> int:
        with self._lock:
            return len(self._contacts)


# ── Singleton ──────────────────────────────────────────────────────────────────

_comms_lock: __import__("threading").Lock = __import__("threading").Lock()
_comms_manager: CommsManager = None


def get_comms_manager() -> CommsManager:
    global _comms_manager
    if _comms_manager is None:
        with _comms_lock:
            if _comms_manager is None:
                _comms_manager = CommsManager()
    return _comms_manager
