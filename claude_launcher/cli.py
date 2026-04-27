"""main() function with argparse for ClaudeLauncher CLI."""

from __future__ import annotations

import argparse
import os
import sys

from .app import App
from .config import ConfigManager
from .constants import LAUNCHER_DIR, VERSIONS_DIR, CLAUDE_SYMLINK
from .health import run_health_check, print_health_report
from .hooks import run_hooks
from .launch import resolve_launch_config, do_launch
from .segment import version_sort_key
from .state import save_launch_state


def _do_launch_sequence(
    cfg: ConfigManager, selections: dict, extra_flags: list[str] | None = None
) -> None:
    """Run health check, hooks, save state, resolve, and exec. Does not return on success."""
    if cfg.config.get("health_check_on_launch", True):
        results = run_health_check()
        warnings = [r for r in results if not r.ok]
        if warnings:
            print("Health warnings:")
            print_health_report(warnings)
            print("Press Enter to continue or Ctrl-C to abort...")
            try:
                input()
            except KeyboardInterrupt:
                print()
                sys.exit(1)
    if not run_hooks("pre-launch", selections):
        print("Pre-launch hook failed. Aborting.")
        sys.exit(1)
    # Save state only after hooks succeed, so launch_count isn't inflated by aborts
    save_launch_state(cfg, selections)
    try:
        cwd, argv, env = resolve_launch_config(
            selections, cfg.options_def, cfg.config.get("default_flags", []),
            extra_flags=extra_flags,
        )
        do_launch(cwd, argv, env)
    except OSError as e:
        print(f"Launch failed: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    # Load config first so we can build dynamic --<segment> CLI args
    cfg = ConfigManager()
    enabled = cfg.config.get("enabled_segments", [])
    segment_keys = [s["key"] for s in cfg.segments_def if s["key"] in enabled]

    parser = argparse.ArgumentParser(prog="c", description="ClaudeLauncher - TUI launcher for Claude Code")
    parser.add_argument("--health", action="store_true", help="run health check and exit")
    parser.add_argument("--config", action="store_true", help="open ~/.claudelauncher/ in $EDITOR")
    parser.add_argument("--versions", action="store_true", help="list available versions and exit")
    parser.add_argument("--install", metavar="VERSION", default=None,
                        help="download and install a specific Claude Code version, then exit")

    # Mutually exclusive session passthrough flags (handed to claude as -c / -r)
    # --resume optionally accepts a session ID; without one, Claude opens its picker.
    _RESUME_NO_ID = object()  # sentinel for "-r with no value"
    session_group = parser.add_mutually_exclusive_group()
    session_group.add_argument("-c", "--continue", dest="cont", action="store_true",
                               help="continue the most recent Claude conversation")
    session_group.add_argument("-r", "--resume", nargs="?", default=None, const=_RESUME_NO_ID,
                               metavar="SESSION_ID",
                               help="resume a Claude session (with optional ID, or open picker)")

    # Dynamic --<segment_key> args, one per enabled segment
    seg_group = parser.add_argument_group("segment values")
    for sdef in cfg.segments_def:
        key = sdef["key"]
        if key in enabled:
            seg_group.add_argument(
                f"--{key}", default=None, metavar="VALUE",
                help=f"preset value for the {sdef.get('label', key)} segment",
            )

    args = parser.parse_args()

    # --versions: list installed versions and exit
    if args.versions:
        if VERSIONS_DIR.is_dir():
            versions = sorted(
                [e.name for e in VERSIONS_DIR.iterdir() if e.is_file()],
                key=version_sort_key,
                reverse=True,
            )
        else:
            versions = []

        # Determine which version the symlink points to
        current_version = None
        try:
            if CLAUDE_SYMLINK.is_symlink() or CLAUDE_SYMLINK.exists():
                target = CLAUDE_SYMLINK.resolve()
                current_version = target.name
        except OSError:
            pass

        if not versions:
            print("No versions found in", VERSIONS_DIR)
        else:
            for v in versions:
                suffix = " (current)" if v == current_version else ""
                print(f"  {v}{suffix}")
        return

    # --config: open config dir in editor
    if args.config:
        editor = os.environ.get("EDITOR", os.environ.get("VISUAL", "vi"))
        os.execlp(editor, editor, str(LAUNCHER_DIR))

    # --health: run health checks and exit
    if args.health:
        results = run_health_check()
        print_health_report(results)
        sys.exit(0 if all(r.ok for r in results) else 1)

    # --install <version>: download and install a version, then exit
    if args.install:
        from .install import install_version

        def on_progress(downloaded: int, total: int) -> None:
            if total > 0:
                mb_done = downloaded / (1024 * 1024)
                mb_total = total / (1024 * 1024)
                pct = downloaded * 100 // total
                print(f"\r  {mb_done:.0f}/{mb_total:.0f} MB ({pct}%)", end="", flush=True)

        print(f"Downloading Claude Code {args.install}...")
        try:
            dest = install_version(args.install, progress_callback=on_progress)
            print(f"\nInstalled to {dest}")
        except OSError as e:
            print(f"\nInstallation failed: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # Collect segment value overrides from CLI args
    segment_overrides: dict[str, str] = {}
    for key in segment_keys:
        val = getattr(args, key, None)
        if val is not None:
            segment_overrides[key] = val

    # Build extra Claude Code flags from passthrough args
    extra_flags: list[str] = []
    if args.cont:
        extra_flags.append("--continue")
    elif args.resume is not None:
        extra_flags.append("--resume")
        if args.resume is not _RESUME_NO_ID:
            extra_flags.append(args.resume)

    # Skip TUI ONLY when the args themselves cover every required segment.
    # Partial args (e.g. just --directory .) always show the TUI with the
    # overrides pre-filled, regardless of what's in last_config.
    required_keys = {s["key"] for s in cfg.segments_def
                     if s["key"] in enabled and s.get("required", False)}
    if required_keys and all(k in segment_overrides for k in required_keys):
        merged = dict(cfg.state.get("last_config", {}))
        merged.update(segment_overrides)
        _do_launch_sequence(cfg, merged, extra_flags=extra_flags)
        return

    # Otherwise show the TUI (pre-filled from last_config + arg overrides)
    app = App(cfg=cfg, overrides=segment_overrides)
    selections = app.run_tui()
    if selections is None:
        return

    _do_launch_sequence(app.cfg, selections, extra_flags=extra_flags)
