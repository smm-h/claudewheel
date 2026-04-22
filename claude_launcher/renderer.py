"""Renderer class for drawing the segment bar TUI."""

from __future__ import annotations

from .constants import (CLEAR_SCREEN, RESET, BOLD, DIM, move_to)
from .segment import Segment, SegmentBar
from .terminal import Terminal
from .theme import ThemeColors


class Renderer:
    """Renders the segment bar centered, with fan-out options and themed colors."""

    def __init__(self, terminal: Terminal, theme: ThemeColors):
        self.term = terminal
        self.theme = theme
        # Tracks where each segment's value is drawn, for fan-out alignment
        self._segment_positions: dict[str, tuple[int, int]] = {}

    def render(self, bar: SegmentBar, flash: str = "") -> None:
        buf: list[str] = [CLEAR_SCREEN]
        center_row = self.term.rows // 2
        self._render_center_line(buf, bar, center_row)
        self._render_fan_out(buf, bar, center_row)
        self._render_status(buf, bar, flash)
        self.term.write("".join(buf))
        self.term.flush()

    def _seg_colors(self, key: str) -> dict[str, str]:
        """Get per-segment color dict, falling back to empty strings."""
        return self.theme.segment_colors.get(key, {})

    def _render_center_line(
        self, buf: list[str], bar: SegmentBar, center_row: int
    ) -> None:
        self._segment_positions.clear()
        th = self.theme
        col = 2  # 1-indexed, with left margin
        sep = th.separator_char

        for i, seg in enumerate(bar.segments):
            is_focused = i == bar.focus_idx
            sc = self._seg_colors(seg.key)
            label_str = seg.label + ": "

            # Determine what to display as the value
            if is_focused and seg.searchable and seg.search_buffer:
                # Show the search buffer text with a cursor
                raw_value = seg.search_buffer
                display_value = self._fit_value(raw_value, seg.min_width, seg.max_width)
            elif seg.value is not None:
                raw_value = seg.value
                display_value = self._fit_value(raw_value, seg.min_width, seg.max_width)
            else:
                raw_value = th.empty_value_text
                display_value = self._fit_value(raw_value, seg.min_width, seg.max_width)

            # Record position of the value (not label) for fan-out alignment
            value_col = col + len(label_str)
            self._segment_positions[seg.key] = (value_col, len(display_value))

            buf.append(move_to(center_row, col))

            if is_focused:
                focus_bg = sc.get("focus_bg", "")
                focus_fg = sc.get("focus_fg", "")
                buf.append(focus_bg + focus_fg)
                buf.append(label_str)
                if seg.searchable and seg.search_buffer:
                    # Render search text + cursor character
                    buf.append(display_value)
                    buf.append(RESET)
                    buf.append(th.search_cursor_fg + "_" + RESET)
                else:
                    buf.append(display_value)
                    buf.append(RESET)
            else:
                # Label in label color, value in per-segment value color
                buf.append(th.label_fg)
                buf.append(label_str)
                buf.append(RESET)
                if seg.value is None:
                    buf.append(th.empty_value_fg)
                    buf.append(display_value)
                    buf.append(RESET)
                else:
                    buf.append(sc.get("value_fg", ""))
                    buf.append(display_value)
                    buf.append(RESET)

            # Advance column past value; add 1 for cursor char if search is active
            extra = 1 if (is_focused and seg.searchable and seg.search_buffer) else 0
            col += len(label_str) + len(display_value) + extra

            # Separator between segments (not after the last one)
            if i < len(bar.segments) - 1:
                buf.append(move_to(center_row, col))
                buf.append(th.separator_fg)
                buf.append(sep)
                buf.append(RESET)
                col += len(sep)

    def _render_fan_out(
        self, buf: list[str], bar: SegmentBar, center_row: int
    ) -> None:
        """Render non-selected options vertically above/below the focused segment."""
        seg = bar.focused
        if not seg.show_options or len(seg.options) <= 1:
            return
        if seg.key not in self._segment_positions:
            return

        value_col, display_width = self._segment_positions[seg.key]
        sc = self._seg_colors(seg.key)
        option_fg = sc.get("option_fg", DIM)

        # Determine which options list and selected index to use
        if seg.search_buffer:
            opts = seg.filtered_options
            if not opts:
                return
            # In search mode, the center line shows the search text,
            # and ALL filtered options fan out below
            above: list[str] = []
            below: list[str] = opts
        else:
            opts = seg.options
            sel_idx = seg.selected_idx if seg.selected_idx >= 0 else 0
            # Options before selected go above (reversed so closest is nearest)
            above = list(reversed(opts[:sel_idx]))
            # Options after selected go below
            below = opts[sel_idx + 1:]

        # Render above options
        for offset, opt_text in enumerate(above, start=1):
            row = center_row - offset
            if row < 1:
                break
            display = self._fit_value(opt_text, seg.min_width, seg.max_width)
            buf.append(move_to(row, value_col))
            buf.append(option_fg)
            buf.append(display)
            buf.append(RESET)

        # Render below options
        for offset, opt_text in enumerate(below, start=1):
            row = center_row + offset
            if row >= self.term.rows:
                break
            display = self._fit_value(opt_text, seg.min_width, seg.max_width)
            buf.append(move_to(row, value_col))
            buf.append(option_fg)
            buf.append(display)
            buf.append(RESET)

    def _render_status(self, buf: list[str], bar: SegmentBar, flash: str = "") -> None:
        buf.append(move_to(self.term.rows, 2))
        if flash:
            # Show flash message prominently (bold + empty_value_fg for visibility)
            buf.append(BOLD + self.theme.empty_value_fg)
            buf.append(flash[: self.term.cols - 4])
            buf.append(RESET)
            return
        seg = bar.focused
        if seg.searchable:
            if seg.search_buffer:
                hints = "type: search   tab: accept   esc: clear   backspace: delete   enter: launch"
            else:
                hints = "type: search   tab: accept   esc: clear   q: quit"
        else:
            hints = "arrows: navigate   enter: launch   q: quit"
        buf.append(DIM)
        buf.append(hints[: self.term.cols - 4])
        buf.append(RESET)

    def _fit_value(self, value: str, min_w: int, max_w: int) -> str:
        """Truncate with ellipsis or pad with spaces to fit width constraints."""
        if len(value) > max_w:
            return value[: max_w - 1] + "\u2026"
        if len(value) < min_w:
            return value + " " * (min_w - len(value))
        return value
