from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

GENESIS = ""


def repo_root() -> Path:
    env = os.environ.get("EAC_ROOT")
    if env:
        return Path(env).resolve()
    start = Path(__file__).resolve()
    for candidate in (start, *start.parents):
        if (candidate / "catalog" / "rules.yaml").is_file():
            return candidate
    raise FileNotFoundError("could not find catalog/rules.yaml from the package location")


def canonical(obj: object) -> bytes:
    text = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return (text + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def now_iso() -> str:
    override = os.environ.get("EAC_NOW")
    if override:
        return override
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git_commit(path: Path, root: Path) -> str:
    try:
        out = subprocess.check_output(
            ["git", "log", "-1", "--format=%H", "--", str(path)],
            cwd=root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "uncommitted"
    return out or "uncommitted"


def rel_posix(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def which_version(argv: list[str]) -> str:
    out = subprocess.check_output(argv, text=True, stderr=subprocess.STDOUT)
    return out.strip()


def pct(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "0.0"
    return f"{(100.0 * numerator / denominator):.1f}"
