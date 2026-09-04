# forge
#!/usr/bin/env python3
"""
forge session-start hook  —  SessionStart lifecycle

Prints a brief forge status snapshot at the beginning of each Claude session.
Only activates when the architecture model exists — no-op on non-forge projects.

Output goes to stderr (rendered as a session note by Claude Code).
No stdin expected for lifecycle hooks. Exit 0 always.

Install via: /forge:init hooks
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from _forge_common import find_meta, forge_paths, load_hook_config, load_yaml, yaml_available


def main() -> None:
    meta = find_meta()
    if meta is None:
        sys.exit(0)
    paths = forge_paths(meta)
    if not paths["architecture"].is_dir():
        sys.exit(0)

    lines: list[str] = []

    # Blocking decisions
    blocking = _count_blocking(paths["decisions"] / "open.yml")
    if blocking is None:
        lines.append("⚠  cannot verify blocking decisions (no YAML library — pip install ruamel.yaml)")
    elif blocking:
        lines.append(
            f"⚠  {blocking} blocking decision(s) → /forge:architect-adr-writer"
        )

    # In-progress kanban cards
    in_progress = _count_in_progress(paths["cards"])
    if in_progress:
        lines.append(
            f"   {in_progress} card(s) in progress → /forge:kanban run resume"
        )

    # Pending calibration suggestions in retro.md
    pending = _count_pending_calibrations(paths["retro"])
    if pending:
        lines.append(
            f"   {pending} calibration suggestion(s) pending → /forge:retrospective calibrate"
        )

    # Cadence layer: everything overdue, one routed line each
    # (audit staleness, risk review, threat-model drift, MET/ASM, postmortems,
    #  escalated cards, unscored backlog, desk orders — computed by status.py).
    for item in _attention(meta):
        lines.append(f"⚑  {item}")

    if lines:
        print("forge:", file=sys.stderr)
        for line in lines:
            print(f"  {line}", file=sys.stderr)


def _attention(meta: Path) -> list[str]:
    """Run status.py --format attention via the plugin dir from config.json.
    Degrades loudly, not silently: a broken setup produces one note, not nothing."""
    cfg = load_hook_config()
    if not cfg:
        return []  # hooks installed without config — attention layer not wired
    try:
        plugin_dir = Path(cfg.get("forge_plugin_dir", ""))
        script = plugin_dir / "skills" / "architect-validate" / "scripts" / "status.py"
        if not script.exists():
            return ["(cadence check unavailable: status.py not found — re-run /forge:init hooks)"]
        out = subprocess.run(
            [sys.executable, str(script), "--meta", str(meta), "--format", "attention"],
            capture_output=True, text=True, timeout=15,
        )
        if out.returncode != 0:
            return []
        return [ln for ln in out.stdout.splitlines() if ln.strip()][:8]
    except subprocess.TimeoutExpired:
        return ["(cadence check timed out — run /forge:status manually)"]
    except Exception:
        return []


def _count_blocking(open_file: Path) -> int | None:
    """None = cannot verify (no YAML lib); int = verified count."""
    if not open_file.exists():
        return 0
    if not yaml_available():
        return None
    data = load_yaml(open_file)
    if data is None:
        return 0
    return sum(
        1 for d in (data.get("open") or [])
        if isinstance(d, dict)
        and d.get("status") == "open" and "synthesis" in (d.get("blocks") or [])
    )


def _count_in_progress(cards_dir: Path) -> int:
    if not cards_dir.is_dir():
        return 0
    count = 0
    for card in cards_dir.glob("*.md"):
        try:
            text = card.read_text(encoding="utf-8", errors="ignore")
            if "Status: in_progress" in text or "Status:** in_progress" in text:
                count += 1
        except Exception:
            pass
    return count


def _count_pending_calibrations(retro_file: Path) -> int:
    if not retro_file.exists():
        return 0
    try:
        text = retro_file.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return 0
    # A suggestion is pending if it has no "applied:" marker on the same or next line
    suggestions = re.findall(r"### Suggestions\n(.*?)(?=\n###|\Z)", text, re.DOTALL)
    count = 0
    for block in suggestions:
        if "none" in block.lower():
            continue
        if "applied:" not in block:
            # count non-empty suggestion lines
            count += sum(1 for ln in block.splitlines() if ln.strip().startswith("-"))
    return count


if __name__ == "__main__":
    main()
