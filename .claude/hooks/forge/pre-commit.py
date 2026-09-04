# forge
#!/usr/bin/env python3
"""
forge pre-commit hook  —  PreToolUse on Bash

Runs forge's deterministic CI gate before git commit (earlier catch than pre-push).
Requires .claude/hooks/forge/config.json with forge_plugin_dir (written by
/forge:init hooks). Falls back to a blocking-decisions check when config is absent —
and SAYS SO (a silently weaker gate reads as a passing full gate).

Exit 0 → allow. Exit 2 → block and show message.

Install via: /forge:init hooks
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from _forge_common import (command_matches, find_meta, forge_paths,
                           load_hook_config, load_yaml, warn, yaml_available)


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    command: str = data.get("tool_input", {}).get("command", "")
    if not command_matches(command, "git", "commit"):
        sys.exit(0)

    meta = find_meta()
    if meta is None or not forge_paths(meta)["architecture"].is_dir():
        sys.exit(0)

    ci_script = _find_ci_script()
    if ci_script:
        _run_ci_gate(ci_script, meta)
    else:
        warn("full CI gate unavailable (config.json missing or forge plugin moved) "
             "— checking blocking decisions only. Re-run /forge:init hooks to restore.")
        _check_blocking_only(meta)


def _find_ci_script() -> Path | None:
    """Locate ci.py via config.json written by forge:init hooks."""
    plugin_dir = load_hook_config().get("forge_plugin_dir", "")
    if not plugin_dir:
        return None
    candidate = Path(plugin_dir) / "skills" / "architect-validate" / "scripts" / "ci.py"
    return candidate if candidate.exists() else None


def _run_ci_gate(ci_script: Path, meta: Path) -> None:
    try:
        result = subprocess.run(
            [sys.executable, str(ci_script), "--meta", str(meta)],
            capture_output=True, text=True, timeout=60,
        )
    except subprocess.TimeoutExpired:
        warn("CI gate timed out (60s) — commit allowed WITHOUT the gate. "
             "Run /forge:ci manually to verify.")
        sys.exit(0)
    except Exception as e:
        warn(f"CI gate failed to run ({e!r}) — commit allowed WITHOUT the gate. "
             "Run /forge:ci manually to verify.")
        sys.exit(0)
    output = result.stdout + result.stderr
    for line in output.splitlines():
        if any(tag in line for tag in ("WARN", "ERROR", "BLOCKED", "✗")):
            print(f"forge(ci): {line}", file=sys.stderr)
    if result.returncode != 0:
        print(
            "\nforge: commit blocked — CI gate failed. Run /forge:ci for details.",
            file=sys.stderr,
        )
        sys.exit(2)


def _check_blocking_only(meta: Path) -> None:
    """Fallback: block only on unresolved blocking decisions."""
    open_file = forge_paths(meta)["decisions"] / "open.yml"
    if not open_file.exists():
        return
    if not yaml_available():
        warn("blocking-decisions check skipped — no YAML library available "
             "(pip install ruamel.yaml); the gate did NOT run.")
        return
    data = load_yaml(open_file)
    if data is None:
        warn(f"blocking-decisions check skipped — could not parse {open_file}.")
        return
    blocking = [
        d for d in (data.get("open") or [])
        if isinstance(d, dict)
        and d.get("status") == "open"
        and "synthesis" in (d.get("blocks") or [])
    ]
    if not blocking:
        return
    warn(f"commit blocked — {len(blocking)} blocking architectural decision(s) unresolved:")
    for d in blocking:
        q = str(d.get("question") or "").replace("\n", " ").strip()
        print(f"  {d.get('id', '?')}: {q[:80]}", file=sys.stderr)
    print("\nResolve with /forge:architect-adr-writer, then commit.", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
