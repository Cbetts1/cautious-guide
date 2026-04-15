"""
AURA — Autonomous Universal Reasoning Assistant
AI engine for AIOS. Starts in rule-based mode.
Designed to swap in an LLM (GGUF/Ollama) without changing
the interface.
"""

import os
import json
import time
import re
from typing import Optional


ROOT       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES_PATH = os.path.join(ROOT, "ai", "rules", "base_rules.json")


class Aura:
    """
    AURA AI Engine.

    mode = "rule"   — built-in pattern matching (default, offline)
    mode = "llm"    — forward to a local LLM (future: llama.cpp / Ollama)
    """

    VERSION = "1.0.0"

    def __init__(self, cfg: dict = None):
        cfg = cfg or {}
        self.mode        = cfg.get("mode", "rule")
        self.model_path  = cfg.get("model_path", "")
        self.context     = []          # conversation history
        self.max_context = cfg.get("context_size", 20)
        self._rules      = self._load_rules()
        self._llm        = None        # LLM handle, loaded on demand

    # ── Internal ──────────────────────────────────────────────────────

    def _load_rules(self) -> list:
        try:
            with open(RULES_PATH) as f:
                return json.load(f)
        except Exception:
            return []

    def _rule_match(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        for rule in self._rules:
            for pattern in rule.get("patterns", []):
                if re.search(r'\b' + re.escape(pattern) + r'\b', text_lower):
                    return rule.get("response", "")
        return None

    def _add_context(self, role: str, text: str):
        self.context.append({"role": role, "text": text, "ts": time.time()})
        if len(self.context) > self.max_context:
            self.context = self.context[-self.max_context:]

    # ── Public API ────────────────────────────────────────────────────

    def query(self, text: str) -> str:
        """
        Send a message to AURA. Returns AURA's response string.
        """
        if not text.strip():
            return ""

        self._add_context("user", text)

        if self.mode == "rule":
            response = self._rule_match(text)
            if response:
                self._add_context("aura", response)
                try:
                    from cc.events import get_event_bus, LEVEL_INFO
                    get_event_bus().emit("AURA", LEVEL_INFO, f"Query matched: {text[:60]}")
                except Exception:
                    pass
                return response
            # Fallback
            resp = self._fallback(text)
            self._add_context("aura", resp)
            try:
                from cc.events import get_event_bus, LEVEL_INFO
                get_event_bus().emit("AURA", LEVEL_INFO, f"Query fallback: {text[:60]}")
            except Exception:
                pass
            return resp

        if self.mode == "llm":
            resp = self._llm_query(text)
            self._add_context("aura", resp)
            return resp

        return "AURA: unknown mode."

    def _fallback(self, text: str) -> str:
        # Provide smart fallback based on keywords
        text_lower = text.lower()
        if any(w in text_lower for w in ["how", "what", "why", "when", "where", "who"]):
            return ("I don't have a specific rule for that yet. "
                    "Check the Help panel or type 'help' in ARROW for available commands. "
                    "AURA grows smarter as rules and models are added.")
        if any(w in text_lower for w in ["run", "execute", "start", "launch"]):
            return "Use ARROW shell to run commands. Press S in the CC to open ARROW, or navigate to ARROW Shell."
        return ("Understood. I'm operating in rule-based mode. "
                "Add an LLM model to config to enable advanced reasoning. "
                "Try 'help' or ask about specific AIOS components.")

    def _llm_query(self, text: str) -> str:
        # Future: integrate llama-cpp-python or Ollama REST API
        # For now, fall back to rules
        response = self._rule_match(text)
        return response or self._fallback(text)

    def load_llm(self, model_path: str) -> bool:
        """
        Attempt to load an LLM. Returns True if successful.
        Tries llama-cpp-python first, then Ollama HTTP fallback.
        """
        try:
            from llama_cpp import Llama  # type: ignore
            self._llm = Llama(model_path=model_path, n_ctx=2048, verbose=False)
            self.mode = "llm"
            self.model_path = model_path
            return True
        except ImportError:
            pass
        except Exception:
            pass
        return False

    def reload_rules(self) -> int:
        """Reload rules from disk without restarting AURA. Returns rule count."""
        self._rules = self._load_rules()
        try:
            from cc.events import get_event_bus, LEVEL_OK
            get_event_bus().emit("AURA", LEVEL_OK,
                                 f"Rules reloaded — {len(self._rules)} rules loaded")
        except Exception:
            pass
        return len(self._rules)

    def get_context(self) -> list:
        return list(self.context)

    def clear_context(self):
        self.context = []

    def get_status(self) -> dict:
        return {
            "version":    self.VERSION,
            "mode":       self.mode,
            "model":      os.path.basename(self.model_path) if self.model_path else "none",
            "rules":      len(self._rules),
            "ctx_items":  len(self.context),
        }


# Singleton
_aura_instance = None


def get_aura() -> Aura:
    global _aura_instance
    if _aura_instance is None:
        try:
            import json
            cfg_path = os.path.join(ROOT, "config", "aios.cfg")
            with open(cfg_path) as f:
                cfg = json.load(f)
            _aura_instance = Aura(cfg.get("aura", {}))
        except Exception:
            _aura_instance = Aura()
    return _aura_instance
