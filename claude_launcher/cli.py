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


def main() -> None:
    parser = argparse.ArgumentParser(prog="c", description="ClaudeLauncher - TUI launcher for Claude Code")
    parser.add_argument("preset", nargs="?", default=None, help="preset name (reserved for future use)")
    parser.add_argument("--last", action="store_true", help="relaunch with last-used config, no TUI")
    parser.add_argument("--pick", action="store_true", help="force TUI even if --last is set")
    parser.add_argument("--health", action="store_true", help="run health check and exit")
    parser.add_argument("--config", action="store_true", help="open ~/.claudelauncher/ in $EDITOR")
    parser.add_argument("--versions", action="store_true", help="list available versions and exit")
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

    # --last (and not --pick): relaunch from saved state
    if args.last and not args.pick:
        cfg = ConfigManager()
        last = cfg.state.get("last_config", {})
        if not last:
            print("No last config found. Run without --last to use the TUI.")
            return
        selections = last
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
                selections, cfg.options_def, cfg.config.get("default_flags", [])
            )
            do_launch(cwd, argv, env)
        except OSError as e:
            print(f"Launch failed: {e}", file=sys.stderr)
            sys.exit(1)
        return  # unreachable after exec, but explicit for clarity

    # Default / --pick: run TUI
    app = App()
    selections = app.run_tui()
    if selections is None:
        return

    # Launch sequence: health check, hooks, save state, resolve config, exec
    # Terminal is already restored by App.run_tui()'s finally block,
    # so health check print/input happens on the normal terminal
    if app.cfg.config.get("health_check_on_launch", True):
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
    save_launch_state(app.cfg, selections)
    try:
        cwd, argv, env = resolve_launch_config(
            selections, app.cfg.options_def, app.cfg.config.get("default_flags", [])
        )
        do_launch(cwd, argv, env)
    except OSError as e:
        print(f"Launch failed: {e}", file=sys.stderr)
        sys.exit(1)
