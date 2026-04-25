"""Segment model, SegmentBar, and option discovery logic."""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from .config import ConfigManager
from .fuzzy import fuzzy_rank

NPM_CACHE_TTL = 3600  # 1 hour


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
    installed: set[str] = field(default_factory=set)  # tracks locally installed options
    creatable: bool = False  # whether this segment supports inline "+" creation
    creating: bool = False   # True when in creation-mode text input
    create_buffer: str = ""  # text being typed for the new option

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
        """Move selection up (+1) or down (-1) through options.

        The ring has n+1 positions: [-1, 0, 1, ..., n-1] where -1 is the
        blank/unselected state. Cycling wraps through all positions including
        blank, so the user can always return to an unselected state.
        """
        if not self.options:
            return
        n = len(self.options)
        # Ring of size n+1: positions are -1, 0, 1, ..., n-1
        # Map -1 -> 0, 0 -> 1, ..., n-1 -> n for ring arithmetic
        ring_pos = self.selected_idx + 1  # now in [0, n]
        ring_pos += direction
        if self.wrap:
            ring_pos %= (n + 1)
        else:
            ring_pos = max(0, min(n, ring_pos))
        self.selected_idx = ring_pos - 1  # back to [-1, n-1]

    @property
    def is_on_plus(self) -> bool:
        """True if the current selection is the '+' creation sentinel."""
        return self.creatable and self.value == "+"

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


def fetch_npm_versions(state: dict, count: int = 15) -> list[str]:
    """Fetch recent Claude Code versions from npm, with 1-hour cache in state."""
    cache = state.get("npm_versions_cache", {})
    cached_at = cache.get("fetched_at", 0)
    cached_versions = cache.get("versions", [])

    if time.time() - cached_at < NPM_CACHE_TTL and cached_versions:
        return cached_versions[-count:]

    try:
        result = subprocess.run(
            ["npm", "view", "@anthropic-ai/claude-code", "versions", "--json"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            all_versions = json.loads(result.stdout)
            # Cache the full list
            state["npm_versions_cache"] = {
                "fetched_at": time.time(),
                "versions": all_versions,
            }
            return all_versions[-count:]
    except Exception:
        pass

    # On failure, use cache even if stale
    if cached_versions:
        return cached_versions[-count:]
    return []


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
                case "npm_and_local":
                    local_path = Path(disc["path"]).expanduser()
                    # Get locally installed versions
                    installed = set()
                    if local_path.is_dir():
                        installed = {e.name for e in local_path.iterdir() if e.is_file()}
                    # Get available versions from npm
                    npm_versions = fetch_npm_versions(state, disc.get("count", 15))
                    # Merge: all npm versions (last N), plus any local-only ones
                    all_versions = list(npm_versions)
                    for v in installed:
                        if v not in all_versions:
                            all_versions.append(v)
                    all_versions.sort(key=version_sort_key, reverse=True)
                    values = all_versions
                    # Store installed set for build_segment_bar to pick up
                    resolved[f"_installed_{key}"] = installed
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
    # Persist npm cache to state.json so it survives even if the user quits without launching
    cfg.save_state()
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
            creatable=sdef.get("creatable", False),
        )
        # Attach installed set if discovery produced one (e.g. npm_and_local)
        installed_key = f"_installed_{sdef['key']}"
        if installed_key in resolved:
            seg.installed = resolved[installed_key]
        # Append "+" creation sentinel for creatable segments
        if seg.creatable:
            seg.options.append("+")
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
