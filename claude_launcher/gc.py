"""Garbage collection for ClaudeLauncher shared infrastructure."""
from __future__ import annotations
import json, time
from pathlib import Path
from .constants import OPTIONS_FILE

SHARED_DIR = Path.home() / ".claude-shared"
ORIGINS_FILE = Path.home() / ".claude-common" / "profile-origins.jsonl"
STALE_THRESHOLD = 30 * 24 * 3600  # 30 days

def _log(msg: str) -> None:
    print(f"[gc] {msg}")


def _known_profiles() -> set[str]:
    known = {"personal", "work", ";/MG"}
    try:
        opts = json.loads(OPTIONS_FILE.read_text())
        known.update(opts.get("profile", {}).get("values", []))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return known


def _clean_sentinels(dry_run: bool) -> int:
    """Remove .stamped-<uuid> sentinel files older than 30 days."""
    if not SHARED_DIR.is_dir():
        return 0
    now, removed = time.time(), 0
    for entry in SHARED_DIR.iterdir():
        if not entry.name.startswith(".stamped-"):
            continue
        try:
            age = now - entry.stat().st_mtime
        except OSError:
            continue
        if age >= STALE_THRESHOLD:
            removed += 1
            if not dry_run:
                entry.unlink(missing_ok=True)
            _log(f"{'would remove' if dry_run else 'removed'} {entry.name} ({age / 86400:.0f}d)")
    return removed


def _compact_origins(dry_run: bool) -> tuple[int, int]:
    """Remove profile-origins.jsonl lines referencing unknown profiles."""
    if not ORIGINS_FILE.is_file():
        return 0, 0
    try:
        lines = ORIGINS_FILE.read_text().splitlines()
    except OSError:
        return 0, 0
    known, kept, removed = _known_profiles(), [], 0
    for line in lines:
        if not line.strip():
            continue
        try:
            if json.loads(line).get("profile") not in known:
                removed += 1
                continue
        except (json.JSONDecodeError, TypeError):
            pass
        kept.append(line)
    if removed > 0 and not dry_run:
        tmp = ORIGINS_FILE.with_suffix(".tmp")
        tmp.write_text("\n".join(kept) + "\n" if kept else "")
        tmp.rename(ORIGINS_FILE)
    return len(kept), removed


def _report_shared_stats() -> None:
    """Print file count and total size of SHARED_DIR by subdirectory."""
    if not SHARED_DIR.is_dir():
        _log("shared store not found"); return
    _log(f"shared store: {SHARED_DIR}")
    rows, tf, tb = [], 0, 0
    for entry in sorted(SHARED_DIR.iterdir(), key=lambda e: e.name):
        if entry.is_dir() and not entry.is_symlink():
            files = [f for f in entry.rglob("*") if f.is_file() and not f.is_symlink()]
            c, s = len(files), sum(f.stat().st_size for f in files)
        elif entry.is_file():
            c, s = 1, entry.stat().st_size
        else:
            continue
        rows.append((entry.name, c, s)); tf += c; tb += s
    for name, c, s in rows:
        _log(f"  {name:<20s} {c:>6d} files  {s / 1024:>10.1f} KB")
    _log(f"  {'TOTAL':<20s} {tf:>6d} files  {tb / 1024:>10.1f} KB")


def run_gc(dry_run: bool = False) -> None:
    """Run garbage collection across shared store and profile infrastructure."""
    if dry_run:
        _log("DRY RUN -- no changes will be made")
    _log(f"sentinels removed: {_clean_sentinels(dry_run)}")
    kept, removed = _compact_origins(dry_run)
    _log(f"profile-origins.jsonl: kept {kept}, removed {removed}")
    _report_shared_stats()
    _log("done")
