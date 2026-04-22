"""Health check utilities for ClaudeLauncher."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class HealthResult:
    ok: bool
    label: str
    detail: str


def check_tmpfs_quota() -> HealthResult:
    """Check /tmp usage percentage via df."""
    try:
        result = subprocess.run(
            ["df", "--output=pcent", "/tmp"],
            capture_output=True, text=True, timeout=3
        )
        lines = result.stdout.strip().split("\n")
        if len(lines) >= 2:
            pct = int(lines[-1].strip().rstrip("%"))
            if pct > 80:
                return HealthResult(False, "tmpfs", f"{pct}% used (>80% threshold)")
            return HealthResult(True, "tmpfs", f"{pct}% used")
    except Exception as e:
        return HealthResult(True, "tmpfs", f"check failed: {e}")
    return HealthResult(True, "tmpfs", "unknown")


def check_tmp_claude_size() -> HealthResult:
    """Check size of /tmp/claude-$UID/ directory."""
    uid = os.getuid()
    tmp_dir = Path(f"/tmp/claude-{uid}")
    if not tmp_dir.exists():
        return HealthResult(True, "/tmp/claude", "not present")
    try:
        total = sum(f.stat().st_size for f in tmp_dir.rglob("*") if f.is_file())
        mb = total / (1024 * 1024)
        if mb > 500:
            return HealthResult(False, "/tmp/claude", f"{mb:.0f} MB (>500 MB threshold)")
        return HealthResult(True, "/tmp/claude", f"{mb:.0f} MB")
    except Exception as e:
        return HealthResult(True, "/tmp/claude", f"check failed: {e}")


def check_ghost_files() -> HealthResult:
    """Check for deleted-but-open files via lsof."""
    try:
        result = subprocess.run(
            ["lsof", "+L1", "-t"],
            capture_output=True, text=True, timeout=5
        )
        pids = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
        count = len(pids)
        if count > 10:
            return HealthResult(False, "ghost files", f"{count} open deleted files")
        return HealthResult(True, "ghost files", f"{count} open deleted files")
    except FileNotFoundError:
        return HealthResult(True, "ghost files", "lsof not found")
    except Exception as e:
        return HealthResult(True, "ghost files", f"check failed: {e}")


def run_health_check() -> list[HealthResult]:
    """Run all health checks and return results."""
    return [check_tmpfs_quota(), check_tmp_claude_size(), check_ghost_files()]


def print_health_report(results: list[HealthResult]) -> None:
    """Print health check results to stdout."""
    for r in results:
        status = "OK" if r.ok else "WARN"
        print(f"  [{status}] {r.label}: {r.detail}")
