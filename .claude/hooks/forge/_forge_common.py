# forge
"""Shared helpers for forge hooks — path resolution that survives worktrees and
non-default `paths.*` config.

Every hook used to hardcode `meta/architecture`, `meta/kanban/cards`, … relative
to the cwd. That silently no-ops (a) in a project that relocates paths via
`meta/.skills.yml → paths.*` and (b) inside a kanban git worktree, where `meta/`
may not exist at the cwd — exactly the phase the hooks are meant to guard.

Hooks import this module by filename (they live in the same directory):

    from _forge_common import find_meta, forge_paths, to_relative, command_matches
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

_HOOK_DIR = Path(__file__).resolve().parent


def load_hook_config() -> dict:
    """config.json written by /forge:init hooks (forge_plugin_dir, paths, …)."""
    try:
        return json.loads((_HOOK_DIR / "config.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def find_meta() -> Path | None:
    """Resolve the project's meta dir; None when this is not a forge project.

    Order: FORGE_META_DIR env → <cwd>/meta → walk up the parents → the MAIN
    repo when cwd is a git worktree (kanban runs implementation agents in
    worktrees; hooks must still see the main repo's meta)."""
    env = os.environ.get("FORGE_META_DIR")
    if env:
        p = Path(env)
        if p.is_dir():
            return p

    cur = Path.cwd()
    for candidate in [cur, *cur.parents]:
        if (candidate / "meta").is_dir():
            return candidate / "meta"
        if (candidate / ".git").exists():
            break  # reached the repo root without finding meta/

    # Worktree case: resolve the main repository via the common git dir.
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, timeout=5,
        )
        common = out.stdout.strip()
        if out.returncode == 0 and common and common not in (".git",):
            main_root = Path(common).resolve().parent
            if (main_root / "meta").is_dir():
                return main_root / "meta"
    except Exception:
        pass
    return None


def forge_paths(meta: Path) -> dict[str, Path]:
    """Resolved artifact paths. Overrides come from config.json `paths`
    (repo-root-relative, mirrored from meta/.skills.yml by /forge:init hooks);
    defaults match shared/skills-config.md."""
    root = meta.parent
    rel = {
        "architecture": "meta/architecture",
        "kanban": "meta/kanban",
        "backlog": "meta/kanban/backlog.md",
        "requirements": None,   # derived below
        "skills_yml": "meta/.skills.yml",
    }
    cfg_paths = load_hook_config().get("paths") or {}
    for key in ("architecture", "kanban", "backlog"):
        v = cfg_paths.get(key)
        if isinstance(v, str) and v.strip():
            rel[key] = v.strip().rstrip("/")
    p = {k: root / v for k, v in rel.items() if v}
    p["decisions"] = p["architecture"] / "decisions"
    p["cards"] = p["kanban"] / "cards"
    p["trace"] = p["architecture"] / "trace.yml"
    p["requirements"] = p["architecture"] / "requirements.yml"
    p["retro"] = p["kanban"] / "retro.md"
    return p


def to_relative(path: str) -> str:
    cwd = os.getcwd()
    if path.startswith(cwd):
        return path[len(cwd):].lstrip("/\\")
    return path


def command_matches(command: str, *words: str) -> bool:
    """True when the shell command actually runs `git <verb>` — word-boundary
    match instead of a naive substring, so `git -C x push`, `git   push`,
    `git commit -am` all match, while `echo "git push"` (quoted) does not."""
    # strip single/double-quoted segments so quoted mentions don't false-positive
    stripped = re.sub(r"'[^']*'|\"[^\"]*\"", "", command)
    verb = words[-1]
    pattern = r"\bgit\b(?:\s+-[A-Za-z]\s+\S+|\s+--?[\w-]+(?:=\S+)?)*\s+" + re.escape(verb) + r"\b"
    return re.search(pattern, stripped) is not None


def load_yaml(path: Path):
    """YAML load with library fallback; None on failure. Callers must treat a
    None from an EXISTING file as 'cannot verify' and say so — not as 'all clear'."""
    try:
        from ruamel.yaml import YAML
        return YAML(typ="safe").load(path.read_text(encoding="utf-8"))
    except ImportError:
        try:
            import yaml
            return yaml.safe_load(path.read_text(encoding="utf-8"))
        except ImportError:
            return None
        except Exception:
            return None
    except Exception:
        return None


def yaml_available() -> bool:
    try:
        import ruamel.yaml  # noqa: F401
        return True
    except ImportError:
        try:
            import yaml  # noqa: F401
            return True
        except ImportError:
            return False


def warn(msg: str) -> None:
    print(f"forge: {msg}", file=sys.stderr)
