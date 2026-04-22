"""Terminal class for raw-mode input handling and screen management."""

from __future__ import annotations

import atexit
import fcntl
import os
import select
import shutil
import struct
import sys
import termios
import tty

from .constants import (ALT_SCREEN_ON, ALT_SCREEN_OFF, HIDE_CURSOR, SHOW_CURSOR, CLEAR_SCREEN)


class Terminal:
    def __init__(self):
        self.fd = sys.stdin.fileno()
        self.old_attrs = None
        self.rows = 24
        self.cols = 80
        self._in_raw = False

    def get_size(self) -> tuple[int, int]:
        try:
            packed = fcntl.ioctl(self.fd, termios.TIOCGWINSZ, b"\x00" * 4)
            rows, cols = struct.unpack("hh", packed)
            return rows, cols
        except OSError:
            size = shutil.get_terminal_size()
            return size.lines, size.columns

    def enter_raw(self) -> None:
        self.old_attrs = termios.tcgetattr(self.fd)
        tty.setcbreak(self.fd)  # cbreak, not raw -- lets Ctrl-C generate SIGINT
        self._in_raw = True
        self.rows, self.cols = self.get_size()
        sys.stdout.write(ALT_SCREEN_ON + HIDE_CURSOR + CLEAR_SCREEN)
        sys.stdout.flush()
        atexit.register(self.exit_raw)

    def exit_raw(self) -> None:
        if self._in_raw and self.old_attrs is not None:
            termios.tcsetattr(self.fd, termios.TCSAFLUSH, self.old_attrs)
            sys.stdout.write(SHOW_CURSOR + ALT_SCREEN_OFF)
            sys.stdout.flush()
            self._in_raw = False

    def read_key(self) -> str:
        """Read a single keypress, decoding escape sequences for arrow keys etc."""
        ch = os.read(self.fd, 1).decode("utf-8", errors="replace")
        if ch == "\x1b":
            # Check if more bytes follow (escape sequence vs bare Esc)
            r, _, _ = select.select([self.fd], [], [], 0.05)
            if r:
                ch2 = os.read(self.fd, 1).decode("utf-8", errors="replace")
                if ch2 == "[":
                    ch3 = os.read(self.fd, 1).decode("utf-8", errors="replace")
                    match ch3:
                        case "A":
                            return "UP"
                        case "B":
                            return "DOWN"
                        case "C":
                            return "RIGHT"
                        case "D":
                            return "LEFT"
                        case "H":
                            return "HOME"
                        case "F":
                            return "END"
                        case _:
                            return f"ESC[{ch3}"
                return "ESC"
            return "ESC"
        if ch in ("\r", "\n"):
            return "ENTER"
        if ch == "\t":
            return "TAB"
        if ch in ("\x7f", "\x08"):
            return "BACKSPACE"
        if ch == "\x03":
            return "CTRL_C"
        return ch

    def write(self, text: str) -> None:
        sys.stdout.write(text)

    def flush(self) -> None:
        sys.stdout.flush()
