"""CC Panel: AI/AURA — conversational AI interface."""
import os
import textwrap


class AuraPanel:
    TITLE = "AI / AURA"

    def __init__(self):
        self._chat = []     # [(role, text)]
        self._input = ""
        self._aura  = None

    def _get_aura(self):
        if self._aura is None:
            try:
                from ai.aura import get_aura
                self._aura = get_aura()
            except Exception:
                pass
        return self._aura

    def render(self, win, y: int, x: int, height: int, width: int,
               kal=None, curses_mod=None):
        c = curses_mod
        row = y

        def addline(text, attr=0):
            nonlocal row
            if row < y + height - 2:
                try:
                    win.addnstr(row, x, text, width - 1, attr)
                except Exception:
                    pass
                row += 1

        aura = self._get_aura()
        status = aura.get_status() if aura else {"mode": "unavailable", "rules": 0}

        addline("  AURA — Autonomous Universal Reasoning Assistant",
                c.color_pair(3) | c.A_BOLD)
        mode_color = c.color_pair(5) if status["mode"] != "unavailable" else c.color_pair(6)
        addline(f"  Mode: {status['mode'].upper()}  |  Rules: {status.get('rules', 0)}  "
                f"|  Context: {status.get('ctx_items', 0)} items",
                mode_color)
        addline("")
        addline("  " + "─" * (width - 4))

        # Chat history
        chat_area_h = height - 7  # reserve bottom for prompt
        chat_rows   = self._chat[-(chat_area_h):]

        for role, text in chat_rows:
            prefix = "  ◈ AURA: " if role == "aura" else "  ▶ You : "
            wrapped = textwrap.wrap(text, width - len(prefix) - 2) or [""]
            for i, wline in enumerate(wrapped):
                indent = prefix if i == 0 else " " * len(prefix)
                attr = c.color_pair(3) if role == "aura" else c.color_pair(2)
                addline(indent + wline, attr)

        # Pad empty rows
        while row < y + height - 3:
            addline("")

        # Input prompt
        if row < y + height - 2:
            try:
                win.addnstr(row, x, "  " + "─" * (width - 4), width - 1)
                row += 1
            except Exception:
                pass
        if row < y + height - 1:
            prompt = f"  ◈ Ask AURA: {self._input}_"
            try:
                win.addnstr(row, x, prompt, width - 1, c.color_pair(3))
            except Exception:
                pass

    def handle_key(self, key, curses_mod=None):
        """Handle keystrokes while AURA panel is active."""
        c = curses_mod
        if key == 10 or key == 13:  # Enter
            if self._input.strip():
                user_text = self._input.strip()
                self._chat.append(("user", user_text))
                aura = self._get_aura()
                if aura:
                    response = aura.query(user_text)
                else:
                    response = "AURA unavailable."
                self._chat.append(("aura", response))
                self._input = ""
        elif key == 127 or key == 263:  # Backspace
            self._input = self._input[:-1]
        elif 32 <= key <= 126:  # Printable
            self._input += chr(key)
