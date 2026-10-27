from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path


class ScannerError(RuntimeError):
    pass


def run_checkov(root: Path, check_ids: list[str]) -> dict:
    if not check_ids:
        raise ScannerError("no Checkov checks configured")
    cmd = [
        "checkov",
        "-d",
        str(root),
        "--framework",
        "terraform",
        "--check",
        ",".join(check_ids),
        "-o",
        "json",
        "--soft-fail",
        "--download-external-modules",
        "false",
        "--skip-path",
        ".terraform",
        "--skip-path",
        ".git",
    ]
    env = os.environ.copy()
    env["CHECKOV_DOWNLOAD_EXTERNAL_MODULES"] = "false"
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, check=False)
    if proc.returncode not in (0, 1):
        raise ScannerError(proc.stderr.strip() or proc.stdout[-2000:] or "checkov failed")
    raw = proc.stdout
    start = raw.find("{")
    if start < 0:
        start = raw.find("[")
    if start < 0:
        raise ScannerError("checkov did not return JSON")
    data = json.loads(raw[start:])
    if isinstance(data, list):
        data = next(item for item in data if item.get("check_type") == "terraform")
    return _slim_checkov(data)


def _slim_checkov(data: dict) -> dict:
    drop = {
        "code_block",
        "entity_tags",
        "connected_node",
        "vulnerability_details",
        "definition_context_file_path",
        "caller_file_path",
        "caller_file_line_range",
        "evaluations",
        "fixed_definition",
        "bc_category",
        "benchmarks",
        "description",
        "short_description",
        "details",
        "check_len",
        "bc_check_id",
        "check_class",
        "resource_address",
        "severity",
    }
    results = data.get("results") or {}
    slim_results = {}
    for key, value in results.items():
        if not isinstance(value, list):
            slim_results[key] = value
            continue
        cleaned = []
        for item in value:
            if isinstance(item, dict):
                cleaned.append({k: v for k, v in item.items() if k not in drop})
            else:
                cleaned.append(item)
        slim_results[key] = cleaned
    return {
        "check_type": data.get("check_type"),
        "results": slim_results,
        "summary": data.get("summary") or {},
    }


def iter_checkov_records(report: dict):
    results = report.get("results") or {}
    for key in ("passed_checks", "failed_checks", "skipped_checks"):
        for item in results.get(key) or []:
            if isinstance(item, dict) and "check_id" in item:
                yield item


def merge_terraform(directory: Path) -> str:
    parts: list[str] = []
    for path in sorted(directory.rglob("*.tf")):
        if ".terraform" in path.parts:
            continue
        parts.append(path.read_text())
    if not parts:
        return ""
    return "\n\n".join(parts) + "\n"


def run_conftest(directory: Path, policy_dir: Path) -> dict:
    text = merge_terraform(directory)
    if not text.strip():
        return {"filename": directory.as_posix(), "failures": [], "successes": 0, "empty": True}
    handle = tempfile.NamedTemporaryFile("w", suffix=".tf", delete=False)
    handle.write(text)
    handle.close()
    path = Path(handle.name)
    try:
        proc = subprocess.run(
            [
                "conftest",
                "test",
                "-p",
                str(policy_dir),
                "-o",
                "json",
                "--no-color",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        path.unlink(missing_ok=True)
    if proc.returncode not in (0, 1) or not proc.stdout.strip():
        detail = (proc.stderr or proc.stdout or "conftest failed").strip()
        raise ScannerError(f"conftest failed on {directory}: {detail}")
    parsed = json.loads(proc.stdout)
    if not parsed:
        raise ScannerError(f"conftest returned an empty result for {directory}")
    result = parsed[0]
    result["failures"] = result.get("failures") or []
    result["empty"] = False
    return result


def policy_directories(root: Path) -> list[Path]:
    found = [root / "lz"]
    known = root / "fixtures" / "known-bad"
    if known.is_dir():
        found.extend(path for path in sorted(known.iterdir()) if path.is_dir())
    for relative in (
        "fixtures/drift/baseline",
        "fixtures/drift/broken",
        "fixtures/pr-preview",
    ):
        path = root / relative
        if path.is_dir():
            found.append(path)
    return found
