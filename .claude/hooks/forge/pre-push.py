# forge
#!/usr/bin/env python3
"""
forge pre-push hook  —  PreToolUse on Bash

Blocks `git push` when there are open architectural decisions that block
synthesis (status: open, blocks: [synthesis]).

Claude Code wires this as a PreToolUse hook on the Bash tool.
The tool input arrives on stdin as JSON: {"tool_name": "Bash", "tool_input": {"command": "..."}}
Exit 0 → allow. Exit 2 → block and show message.

Install via: /forge:init hooks
"""
from __future__ import annotations

import json
import sys

from _forge_common import command_matches, find_meta, forge_paths, load_yaml, warn, yaml_available


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    command: str = data.get("tool_input", {}).get("command", "")
    if not command_matches(command, "git", "push"):
        sys.exit(0)

    meta = find_meta()
    if meta is None:
        sys.exit(0)
    open_file = forge_paths(meta)["decisions"] / "open.yml"
    if not open_file.exists():
        sys.exit(0)

    if not yaml_available():
        # Degrade LOUDLY, not silently: the gate cannot run, say so and allow.
        warn("pre-push gate skipped — no YAML library available "
             "(pip install ruamel.yaml); blocking decisions NOT verified.")
        sys.exit(0)

    data = load_yaml(open_file)
    if data is None:
        warn(f"pre-push gate skipped — could not parse {open_file}; "
             "blocking decisions NOT verified.")
        sys.exit(0)

    blocking = [
        d for d in (data.get("open") or [])
        if isinstance(d, dict)
        and d.get("status") == "open"
        and "synthesis" in (d.get("blocks") or [])
    ]
    if not blocking:
        sys.exit(0)

    warn(f"push blocked — {len(blocking)} blocking architectural decision(s) unresolved:")
    for d in blocking:
        q = str(d.get("question") or "").replace("\n", " ").strip()
        print(f"  {d.get('id', '?')}: {q[:80]}", file=sys.stderr)
    print("\nResolve with /forge:architect-adr-writer, then push.", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
