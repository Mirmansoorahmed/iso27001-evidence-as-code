from __future__ import annotations

from pathlib import Path

import yaml


def load_fixture_expectations(root: Path) -> list[dict]:
    base = root / "fixtures" / "known-bad"
    found = []
    for path in sorted(base.glob("*/expected.yaml")):
        data = yaml.safe_load(path.read_text())
        data["directory"] = path.parent.relative_to(root).as_posix()
        found.append(data)
    return found


def _classify(expected: str, observed: str) -> str:
    if expected == "fail" and observed == "fail":
        return "tp"
    if expected == "pass" and observed == "pass":
        return "tn"
    if expected == "pass" and observed == "fail":
        return "fp"
    if expected == "fail" and observed == "pass":
        return "fn"
    if expected == "fail" and observed == "absent":
        return "fn"
    return "unevaluated"


def score_fixtures(
    fixtures: list[dict],
    evidence: list[dict],
    *,
    rego_ids: list[str],
) -> dict:
    totals = {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "unevaluated": 0}
    rows = []
    rego = set(rego_ids)
    for fixture in fixtures:
        directory = fixture["directory"]
        expect_fail = set(fixture.get("expect_fail") or [])
        scoped = [
            item
            for item in evidence
            if item["subject"]["file"] == directory
            or item["subject"]["file"].startswith(directory + "/")
        ]
        checkov: dict[str, str] = {}
        rego_failed: set[str] = set()
        for item in scoped:
            rule_id = item["source"]["rule"]
            if item["source"]["tool"] == "checkov":
                if item["result"] == "fail":
                    checkov[rule_id] = "fail"
                elif rule_id not in checkov:
                    checkov[rule_id] = "pass"
            elif item["result"] == "fail":
                rego_failed.add(rule_id)
        pairs = []
        for rule_id in rego_ids:
            observed = "fail" if rule_id in rego_failed else "pass"
            expected = "fail" if rule_id in expect_fail else "pass"
            kind = _classify(expected, observed)
            totals[kind] += 1
            pairs.append({"rule": rule_id, "expected": expected, "observed": observed, "kind": kind})
        for rule_id, observed in sorted(checkov.items()):
            expected = "fail" if rule_id in expect_fail else "pass"
            kind = _classify(expected, observed)
            totals[kind] += 1
            pairs.append({"rule": rule_id, "expected": expected, "observed": observed, "kind": kind})
        for rule_id in sorted(expect_fail - rego - set(checkov)):
            kind = _classify("fail", "absent")
            totals[kind] += 1
            pairs.append({"rule": rule_id, "expected": "fail", "observed": "absent", "kind": kind})
        rows.append(
            {
                "id": fixture["id"],
                "description": fixture.get("description", ""),
                "negative_control": bool(fixture.get("negative_control")),
                "pairs": pairs,
            }
        )
    misconfigured = sum(1 for row in rows if not row["negative_control"])
    negative = sum(1 for row in rows if row["negative_control"])
    return {
        "misconfigured": misconfigured,
        "negative_controls": negative,
        "evaluated_pairs": sum(totals.values()),
        "true_positive": totals["tp"],
        "false_positive": totals["fp"],
        "false_negative": totals["fn"],
        "true_negative": totals["tn"],
        "unevaluated": totals["unevaluated"],
        "fixtures": rows,
        "note": (
            "These fixtures and the policies were written together, so a clean "
            "score mostly shows the pipeline still matches its own labels. "
            "The TerraGoat numbers are the less circular check."
        ),
    }


def score_expectations(expected: dict, evidence: list[dict], *, group: str) -> dict:
    """Score a flat expect-map (used for the TerraGoat held-out set)."""
    spec = expected[group]
    totals = {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "unevaluated": 0}
    observed: dict[str, str] = {}
    for item in evidence:
        rule_id = item["source"]["rule"]
        if rule_id not in spec:
            continue
        if item["result"] == "fail":
            observed[rule_id] = "fail"
        elif rule_id not in observed:
            observed[rule_id] = "pass"
    fn_rules = []
    fp_rules = []
    pairs = []
    for rule_id, meta in spec.items():
        expect = meta["expect"]
        seen = observed.get(rule_id, "absent")
        kind = _classify(expect, seen)
        totals[kind] += 1
        if kind == "fn":
            fn_rules.append(rule_id)
        if kind == "fp":
            fp_rules.append(rule_id)
        pairs.append(
            {
                "rule": rule_id,
                "expected": expect,
                "observed": seen,
                "kind": kind,
                "explicit": meta.get("explicit"),
                "why": meta.get("why", ""),
            }
        )
    return {
        "true_positive": totals["tp"],
        "false_positive": totals["fp"],
        "false_negative": totals["fn"],
        "true_negative": totals["tn"],
        "unevaluated": totals["unevaluated"],
        "fn_rules": fn_rules,
        "fp_rules": fp_rules,
        "pairs": pairs,
    }
