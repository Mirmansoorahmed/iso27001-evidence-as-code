from __future__ import annotations

from pathlib import Path

import yaml

from eac.util import repo_root


def load_catalogue(root: Path | None = None) -> dict:
    root = root or repo_root()
    rules = yaml.safe_load((root / "catalog" / "rules.yaml").read_text())
    annex = yaml.safe_load((root / "catalog" / "annex_a.yaml").read_text())
    rules["annex_a"] = annex["controls"]
    rules["annex_version"] = annex.get("version", rules["version"])
    return rules


def rule_index(catalogue: dict) -> dict[str, dict]:
    return {rule["id"]: rule for rule in catalogue["rules"]}


def checkov_ids(catalogue: dict) -> list[str]:
    return [rule["id"] for rule in catalogue["rules"] if rule["tool"] == "checkov"]


def rego_ids(catalogue: dict) -> list[str]:
    return [rule["id"] for rule in catalogue["rules"] if rule["tool"] == "conftest"]


def control_refs_for(rule: dict) -> list[dict]:
    refs: list[dict] = []
    for control_id in rule.get("iso", []):
        refs.append({"framework": "iso27001-2022", "id": control_id})
    for control_id in rule.get("c5", []):
        refs.append({"framework": "bsi-c5-2020", "id": control_id})
    for control_id in rule.get("grundschutz", []):
        refs.append({"framework": "it-grundschutz", "id": control_id})
    for control_id in rule.get("dora", []):
        refs.append({"framework": "dora", "id": control_id})
    for control_id in rule.get("nis2", []):
        refs.append({"framework": "nis2", "id": control_id})
    return refs


def rules_by_iso(catalogue: dict) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for rule in catalogue["rules"]:
        for control_id in rule.get("iso", []):
            mapping.setdefault(control_id, []).append(rule["id"])
    return mapping
