"""App class -- TUI event loop for ClaudeLauncher."""

from __future__ import annotations

import signal
import subprocess
import sys

from .config import ConfigManager
from .segment import Segment, build_segment_bar, evaluate_requires
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
        self._pending_install: str | None = None  # version awaiting install confirmation
        self._pending_install_seg: Segment | None = None

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
            evaluate_requires(self.bar)
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
                evaluate_requires(self.bar)
                self.renderer.render(self.bar, self._flash)
                self._flash = ""  # Clear flash after one render cycle
        finally:
            self.terminal.exit_raw()

    def _handle_key(self, key: str) -> str | None:
        """Process a keypress and return an action string or None to continue."""
        focused = self.bar.focused

        # Creation mode intercepts all keys
        if focused.creating:
            return self._handle_create_key(key, focused)

        # Freeform editing mode: when a freeform segment has an active search buffer,
        # treat it like a text input (UP/DOWN/LEFT/RIGHT don't destroy the buffer)
        if focused.freeform and focused.search_buffer:
            return self._handle_freeform_key(key, focused)

        # Pending install confirmation
        if self._pending_install:
            return self._handle_install_key(key)

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
                # Enter creation mode if on the "+" sentinel
                if focused.is_on_plus:
                    focused.creating = True
                    focused.create_buffer = ""
                    return None
                # Check for required segments without a selection
                missing = [
                    s.label
                    for s in self.bar.segments
                    if s.required and s.value is None
                ]
                if missing:
                    self._flash = f"Required: {', '.join(missing)}"
                    return None
                # Check for non-installed version -- offer to install
                for s in self.bar.segments:
                    if s.value and s.installed and s.value not in s.installed:
                        self._pending_install = s.value
                        self._pending_install_seg = s
                        self._flash = f"{s.value} not on disk. Enter=install, Esc=cancel"
                        return None
                # Check for unavailable selections
                for s in self.bar.segments:
                    if s.value and s.value in s.unavailable:
                        self._flash = f"{s.label}: {s.value} not available for this version"
                        return None
                return "launch"
            case "TAB":
                # Enter creation mode if on the "+" sentinel
                if focused.is_on_plus:
                    focused.creating = True
                    focused.create_buffer = ""
                    return None
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

    def _handle_freeform_key(self, key: str, seg: Segment) -> str | None:
        """Handle keystrokes in freeform editing mode (search buffer active on a freeform segment)."""
        match key:
            case "ENTER":
                # Submit the typed text as the value
                text = seg.search_buffer.strip()
                if text:
                    if text not in seg.options:
                        seg.options.append(text)
                    seg.select_value(text)
                seg.search_buffer = ""
                if seg.tab_advances:
                    self.bar.move_focus(1)
                return None
            case "TAB":
                # Accept the top fuzzy match (not the raw text)
                matches = seg.filtered_options
                if matches:
                    seg.select_value(matches[0])
                seg.search_buffer = ""
                if seg.tab_advances:
                    self.bar.move_focus(1)
                return None
            case "BACKSPACE":
                seg.search_buffer = seg.search_buffer[:-1]
                return None
            case "ESC":
                seg.search_buffer = ""
                return None
            case "CTRL_C":
                seg.search_buffer = ""
                return "quit"
            case _:
                if len(key) == 1 and key.isprintable():
                    seg.search_buffer += key
        return None

    def _handle_install_key(self, key: str) -> str | None:
        """Handle keystrokes during install confirmation."""
        version = self._pending_install
        seg = self._pending_install_seg
        self._pending_install = None
        self._pending_install_seg = None

        if key != "ENTER" or not version or not seg:
            return None

        # Exit alt screen so the user sees npm output
        self.terminal.exit_raw()
        print(f"Installing @anthropic-ai/claude-code@{version}...")
        result = subprocess.run(
            ["npm", "install", "-g", f"@anthropic-ai/claude-code@{version}"],
        )
        if result.returncode == 0:
            print("Installed successfully. Press Enter to continue...")
            seg.installed.add(version)
        else:
            print("Installation failed. Press Enter to continue...")
        try:
            input()
        except KeyboardInterrupt:
            pass
        # Re-enter alt screen
        self.terminal.enter_raw()
        return None

    def _handle_create_key(self, key: str, seg: Segment) -> str | None:
        """Handle keystrokes while in creation mode."""
        match key:
            case "ENTER":
                if seg.create_buffer.strip():
                    self._confirm_create(seg)
                return None
            case "ESC":
                seg.creating = False
                seg.create_buffer = ""
                return None
            case "BACKSPACE":
                seg.create_buffer = seg.create_buffer[:-1]
                return None
            case "CTRL_C":
                seg.creating = False
                seg.create_buffer = ""
                return "quit"
            case _:
                if len(key) == 1 and key.isprintable():
                    seg.create_buffer += key
        return None

    def _confirm_create(self, seg: Segment) -> None:
        """Confirm creation of a new option."""
        name = seg.create_buffer.strip()
        seg.creating = False
        seg.create_buffer = ""

        if not name or name == "+" or name in seg.options:
            return  # invalid or duplicate

        # Insert before the "+" sentinel
        plus_idx = seg.options.index("+")
        seg.options.insert(plus_idx, name)
        seg.select_value(name)

        # Persist to options.json
        self.cfg.add_option(seg.key, name)
