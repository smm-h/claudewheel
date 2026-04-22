"""Segment model, SegmentBar, and option discovery logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .config import ConfigManager
from .fuzzy import fuzzy_rank


@dataclass
class Segment:
    key: str
    label: str
    options: list[str] = field(default_factory=list)
    selected_idx: int = -1  # -1 means nothing selected
    search_buffer: str = ""
    show_options: bool = True
    wrap: bool = True
    min_width: int = 6
    max_width: int = 20
    required: bool = False
    searchable: bool = False
    tab_advances: bool = True

    @property
    def value(self) -> str | None:
        if self.selected_idx < 0 or not self.options:
            return None
        return self.options[self.selected_idx]

    @property
    def filtered_options(self) -> list[str]:
        """Return options filtered by search_buffer using fuzzy matching."""
        if not self.search_buffer:
            return self.options
        return fuzzy_rank(self.search_buffer, self.options)

    def cycle(self, direction: int) -> None:
        """Move selection up (+1) or down (-1) through options."""
        if not self.options:
            return
        n = len(self.options)
        if self.selected_idx < 0:
            # First interaction: jump to start or end depending on direction
            self.selected_idx = 0 if direction > 0 else n - 1
            return
        new = self.selected_idx + direction
        if self.wrap:
            self.selected_idx = new % n
        else:
            self.selected_idx = max(0, min(n - 1, new))

    def select_value(self, val: str) -> bool:
        """Select an option by its string value. Returns True if found."""
        try:
            self.selected_idx = self.options.index(val)
            return True
        except ValueError:
            return False


@dataclass
class SegmentBar:
    segments: list[Segment] = field(default_factory=list)
    focus_idx: int = 0

    @property
    def focused(self) -> Segment:
        if not self.segments:
            raise RuntimeError("SegmentBar has no segments -- check enabled_segments config")
        return self.segments[self.focus_idx]

    def move_focus(self, direction: int) -> None:
        if not self.segments:
            return
        n = len(self.segments)
        self.focus_idx = (self.focus_idx + direction) % n

    def get_selections(self) -> dict[str, str | None]:
        return {s.key: s.value for s in self.segments}


def version_sort_key(version: str) -> list[int]:
    """Split a version string on '.' and convert parts to ints for numeric sorting."""
    parts = []
    for part in version.split("."):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(0)
    return parts


def discover_options(options_def: dict, state: dict) -> dict[str, list[str]]:
    """Resolve option lists, running discovery (directory listing, state merge) as needed."""
    resolved = {}
    for key, opt in options_def.items():
        values = list(opt.get("values", []))
        disc = opt.get("discovery")
        if disc:
            match disc["type"]:
                case "directory_listing":
                    path = Path(disc["path"]).expanduser()
                    if path.is_dir():
                        # Discover versions from filesystem, sorted newest-first
                        entries = sorted(
                            [e.name for e in path.iterdir() if e.is_file()],
                            key=version_sort_key,
                            reverse=True,
                        )
                        values = entries
                case "state_field":
                    # Merge state-tracked values with static defaults, preserving order
                    state_values = state.get(disc["field"], [])
                    seen: set[str] = set()
                    merged: list[str] = []
                    for v in state_values + values:
                        if v not in seen:
                            seen.add(v)
                            merged.append(v)
                    values = merged
        resolved[key] = values
    return resolved


def build_segment_bar(cfg: ConfigManager) -> SegmentBar:
    """Construct the segment bar from config, applying discovery and last-state restore."""
    enabled = cfg.config.get("enabled_segments", [])
    resolved = discover_options(cfg.options_def, cfg.state)
    segments: list[Segment] = []

    for sdef in cfg.segments_def:
        if sdef["key"] not in enabled:
            continue
        opts = resolved.get(sdef["key"], [])
        seg = Segment(
            key=sdef["key"],
            label=sdef["label"],
            options=opts,
            show_options=sdef.get("show_options", True),
            wrap=sdef.get("wrap", True),
            min_width=sdef.get("min_width", 6),
            max_width=sdef.get("max_width", 20),
            required=sdef.get("required", False),
            searchable=sdef.get("searchable", False),
            tab_advances=sdef.get("tab_advances", True),
        )
        # Pre-select from last session's config if available
        last = cfg.state.get("last_config", {})
        if sdef["key"] in last:
            seg.select_value(last[sdef["key"]])
        segments.append(seg)

    # Auto-detect cwd for the directory segment if nothing was restored
    try:
        cwd = Path.cwd()
        home = Path.home()
        rel = cwd.relative_to(home)
        # When cwd IS home, relative_to returns '.', which would give "~/."
        cwd_tilde = "~" if str(rel) == "." else "~/" + str(rel)
        for seg in segments:
            if seg.key == "directory" and seg.selected_idx < 0:
                seg.select_value(cwd_tilde)
    except ValueError:
        pass

    if not segments:
        raise RuntimeError(
            "No segments enabled -- check enabled_segments in config.json"
        )

    return SegmentBar(segments=segments)
