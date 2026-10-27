from __future__ import annotations

import re
import uuid
from pathlib import Path

from eac.catalogue import control_refs_for, rule_index
from eac.models import EvidenceRecord
from eac.scanners import iter_checkov_records
from eac.util import canonical, git_commit, rel_posix, sha256_bytes

NAMESPACE = uuid.UUID("6f0c1d3e-1a4b-4c5d-8e9f-0a1b2c3d4e5d")
RESOURCE_RE = re.compile(r"(azurerm_[a-z0-9_]+)\.([A-Za-z0-9_-]+)")


def _evidence_id(tool: str, rule: str, resource: str, file: str, result: str) -> str:
    key = "|".join([tool, rule, resource, file, result])
    return str(uuid.uuid5(NAMESPACE, key))


def _record(payload: dict) -> dict:
    return EvidenceRecord.model_validate(payload).model_dump()


def from_checkov(
    report: dict,
    *,
    root: Path,
    catalogue: dict,
    version: str,
    observed_at: str,
    prev_manifest_sha256: str,
) -> list[dict]:
    rules = rule_index(catalogue)
    records: list[dict] = []
    for item in iter_checkov_records(report):
        rule_id = item["check_id"]
        rule = rules.get(rule_id)
        if rule is None:
            continue
        result_name = (item.get("check_result") or {}).get("result", "")
        if result_name == "PASSED":
            result = "pass"
        elif result_name == "FAILED":
            result = "fail"
        elif result_name == "UNKNOWN":
            continue
        else:
            continue
        abs_path = item.get("file_abs_path") or item.get("file_path") or ""
        file_rel = rel_posix(Path(abs_path), root) if abs_path else ""
        resource = item.get("resource") or "unknown"
        slice_obj = {
            "check_id": rule_id,
            "check_name": item.get("check_name"),
            "file": file_rel,
            "resource": resource,
            "result": result_name,
            "guideline": item.get("guideline"),
        }
        digest = sha256_bytes(canonical(slice_obj))
        records.append(
            _record(
                {
                    "evidence_id": _evidence_id("checkov", rule_id, resource, file_rel, result),
                    "control_refs": control_refs_for(rule),
                    "source": {
                        "tool": "checkov",
                        "version": version,
                        "rule": rule_id,
                        "mode": "offline",
                    },
                    "subject": {
                        "resource": resource,
                        "file": file_rel,
                        "commit": git_commit(root / file_rel, root) if file_rel else "uncommitted",
                    },
                    "result": result,
                    "observed_at": observed_at,
                    "sha256": digest,
                    "prev_manifest_sha256": prev_manifest_sha256,
                    "detail": item.get("check_name") or rule["title"],
                }
            )
        )
    return records


def from_conftest(
    scans: list[dict],
    *,
    root: Path,
    catalogue: dict,
    version: str,
    observed_at: str,
    prev_manifest_sha256: str,
    rego_ids: list[str],
) -> list[dict]:
    rules = rule_index(catalogue)
    records: list[dict] = []
    for scan in scans:
        directory: Path = scan["directory"]
        result = scan["result"]
        file_rel = rel_posix(directory, root)
        failures = result.get("failures") or []
        failed_rules: dict[str, list[dict]] = {rule_id: [] for rule_id in rego_ids}
        for failure in failures:
            message = failure.get("msg") or ""
            rule_id = message.split(":", 1)[0].strip()
            if rule_id not in failed_rules:
                continue
            failed_rules[rule_id].append(failure)
        commit = git_commit(directory, root)
        for rule_id, items in failed_rules.items():
            rule = rules[rule_id]
            if not items:
                slice_obj = {
                    "tool": "conftest",
                    "file": file_rel,
                    "rule": rule_id,
                    "result": "pass",
                    "conftest_successes": result.get("successes", 0),
                    "denies": 0,
                }
                digest = sha256_bytes(canonical(slice_obj))
                records.append(
                    _record(
                        {
                            "evidence_id": _evidence_id("conftest", rule_id, "(module)", file_rel, "pass"),
                            "control_refs": control_refs_for(rule),
                            "source": {
                                "tool": "conftest",
                                "version": version,
                                "rule": rule_id,
                                "mode": "offline",
                            },
                            "subject": {
                                "resource": "(module)",
                                "file": file_rel,
                                "commit": commit,
                            },
                            "result": "pass",
                            "observed_at": observed_at,
                            "sha256": digest,
                            "prev_manifest_sha256": prev_manifest_sha256,
                            "detail": rule["title"],
                        }
                    )
                )
                continue
            for failure in items:
                message = failure.get("msg") or rule["title"]
                match = RESOURCE_RE.search(message)
                resource = f"{match.group(1)}.{match.group(2)}" if match else "(module)"
                slice_obj = {
                    "tool": "conftest",
                    "file": file_rel,
                    "rule": rule_id,
                    "result": "fail",
                    "message": message,
                }
                digest = sha256_bytes(canonical(slice_obj))
                records.append(
                    _record(
                        {
                            "evidence_id": _evidence_id("conftest", rule_id, resource, file_rel, "fail"),
                            "control_refs": control_refs_for(rule),
                            "source": {
                                "tool": "conftest",
                                "version": version,
                                "rule": rule_id,
                                "mode": "offline",
                            },
                            "subject": {
                                "resource": resource,
                                "file": file_rel,
                                "commit": commit,
                            },
                            "result": "fail",
                            "observed_at": observed_at,
                            "sha256": digest,
                            "prev_manifest_sha256": prev_manifest_sha256,
                            "detail": message,
                        }
                    )
                )
    return records
