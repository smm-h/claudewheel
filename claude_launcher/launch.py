"""Launch logic for resolving selections into a Claude Code invocation."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .constants import VERSIONS_DIR, CLAUDE_SYMLINK


def fetch_gh_token(account: str) -> str | None:
    """Fetch GH token live via gh CLI. Returns None on failure."""
    try:
        result = subprocess.run(
            ["gh", "auth", "token", "--user", account],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def resolve_launch_config(
    selections: dict[str, str | None],
    options_def: dict,
    default_flags: list[str],
) -> tuple[str, list[str], dict[str, str]]:
    """Build (cwd, argv, env) for os.execvpe from TUI selections.

    Maps segment values to their concrete effects:
    - profile -> CLAUDE_CONFIG_DIR env var (from options.json metadata)
    - github -> GH_TOKEN env var (fetched live via gh CLI)
    - version -> binary path (under ~/.local/share/claude/versions/)
    - directory -> os.chdir target
    - mcp -> --strict-mcp-config flag (if "strict")
    - permissions -> --dangerously-skip-permissions or --permission-mode=X
    """
    # 1. Profile -> config dir
    profile = selections.get("profile")
    config_dir = str(Path("~/.claude").expanduser())
    if profile:
        meta = options_def.get("profile", {}).get("metadata", {})
        profile_meta = meta.get(profile, {})
        if "config_dir" in profile_meta:
            config_dir = str(Path(profile_meta["config_dir"]).expanduser())

    # 2. GH token
    gh_account = selections.get("github")
    gh_token = fetch_gh_token(gh_account) if gh_account else None

    # 3. Version -> binary path
    version = selections.get("version")
    if version:
        binary_path = str(VERSIONS_DIR / version)
        if not (VERSIONS_DIR / version).is_file():
            raise OSError(
                f"Version {version} is not installed. "
                f"Install it with: npm install -g @anthropic-ai/claude-code@{version}"
            )
    else:
        # Fall back to the symlink if no version selected
        binary_path = str(CLAUDE_SYMLINK)

    # 4. Directory -> cwd
    directory = selections.get("directory")
    if directory:
        cwd = str(Path(directory).expanduser())
    else:
        cwd = os.getcwd()

    # 5. MCP flags
    mcp = selections.get("mcp")
    mcp_flags = ["--strict-mcp-config"] if mcp == "strict" else []

    # 5b. Model flag
    model_name = selections.get("model")
    model_flags: list[str] = []
    if model_name:
        model_meta = options_def.get("model", {}).get("metadata", {})
        model_id = model_meta.get(model_name, {}).get("model_id")
        if model_id:
            model_flags = ["--model", model_id]

    # 6. Permission flags
    perm = selections.get("permissions")
    perm_flags: list[str] = []
    if perm == "bypass":
        perm_flags = ["--dangerously-skip-permissions"]
    elif perm in ("default", "plan", "auto"):
        perm_flags = [f"--permission-mode={perm}"]

    # 7. Environment
    env = dict(os.environ)
    env["CLAUDE_CONFIG_DIR"] = config_dir
    if gh_token:
        env["GH_TOKEN"] = gh_token

    # 8. Argv
    argv = [binary_path] + default_flags + mcp_flags + perm_flags + model_flags

    return (cwd, argv, env)


def do_launch(cwd: str, argv: list[str], env: dict[str, str]) -> None:
    """Change to directory and exec Claude Code. Does not return."""
    os.chdir(cwd)
    os.execvpe(argv[0], argv, env)
