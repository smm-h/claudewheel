"""App class -- TUI event loop for ClaudeLauncher."""

from __future__ import annotations

import signal
import sys

from .config import ConfigManager
from .segment import build_segment_bar
from .terminal import Terminal
from .theme import parse_theme
from .renderer import Renderer


class App:
    def __init__(self):
        self.cfg = ConfigManager()
        self.bar = build_segment_bar(self.cfg)
        self.terminal = Terminal()
        self.theme = parse_theme(self.cfg.theme)
        self.renderer = Renderer(self.terminal, self.theme)
        self.running = False
        self._flash: str = ""  # Temporary message shown for one render cycle

    def run_tui(self) -> dict[str, str | None] | None:
        """Enter the TUI loop. Returns selections on launch, None on quit."""
        self.running = True
        self.terminal.enter_raw()

        def on_resize(signum, frame):
            self.terminal.rows, self.terminal.cols = self.terminal.get_size()
            self.renderer.render(self.bar)

        signal.signal(signal.SIGWINCH, on_resize)

        def on_term(signum, frame):
            self.terminal.exit_raw()
            sys.exit(1)

        signal.signal(signal.SIGTERM, on_term)
        signal.signal(signal.SIGHUP, on_term)

        try:
            self.renderer.render(self.bar)
            while self.running:
                try:
                    key = self.terminal.read_key()
                except KeyboardInterrupt:
                    return None
                action = self._handle_key(key)
                if action == "launch":
                    return self.bar.get_selections()
                elif action == "quit":
                    return None
                self.renderer.render(self.bar, self._flash)
                self._flash = ""  # Clear flash after one render cycle
        finally:
            self.terminal.exit_raw()

    def _handle_key(self, key: str) -> str | None:
        """Process a keypress and return an action string or None to continue."""
        focused = self.bar.focused

        match key:
            case "LEFT":
                focused.search_buffer = ""
                self.bar.move_focus(-1)
            case "RIGHT":
                focused.search_buffer = ""
                self.bar.move_focus(1)
            case "UP":
                if focused.search_buffer:
                    focused.search_buffer = ""
                focused.cycle(-1)
            case "DOWN":
                if focused.search_buffer:
                    focused.search_buffer = ""
                focused.cycle(1)
            case "ENTER":
                # Only launch if all required segments have a selection
                missing = [
                    s.label
                    for s in self.bar.segments
                    if s.required and s.value is None
                ]
                if not missing:
                    return "launch"
                # Flash a message so the user knows why ENTER was blocked
                self._flash = f"Required: {', '.join(missing)}"
            case "TAB":
                if focused.searchable and focused.search_buffer:
                    # Accept the top fuzzy match
                    matches = focused.filtered_options
                    if matches:
                        focused.select_value(matches[0])
                    focused.search_buffer = ""
                    if focused.tab_advances:
                        self.bar.move_focus(1)
                elif focused.tab_advances:
                    self.bar.move_focus(1)
            case "BACKSPACE":
                if focused.searchable and focused.search_buffer:
                    focused.search_buffer = focused.search_buffer[:-1]
            case "ESC":
                focused.search_buffer = ""
            case "CTRL_C":
                return "quit"
            case _:
                # Single printable characters
                if len(key) == 1 and key.isprintable():
                    if focused.searchable and (focused.search_buffer or key != "q"):
                        focused.search_buffer += key
                    elif key == "q":
                        return "quit"
        return None
