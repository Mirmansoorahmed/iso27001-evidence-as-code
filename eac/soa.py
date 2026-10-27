from __future__ import annotations

from collections import defaultdict

from eac.catalogue import rules_by_iso
from eac.util import pct


def _in_scope(record: dict, prefix: str) -> bool:
    file_name = record["subject"]["file"]
    return file_name == prefix or file_name.startswith(prefix.rstrip("/") + "/")


def rollup(catalogue: dict, evidence: list[dict], scope: str) -> list[dict]:
    by_iso = rules_by_iso(catalogue)
    scoped = [record for record in evidence if _in_scope(record, scope)]
    fails: dict[str, set[str]] = defaultdict(set)
    passes: dict[str, set[str]] = defaultdict(set)
    last_seen: dict[str, str] = {}
    evidence_ids: dict[str, list[str]] = defaultdict(list)
    for record in scoped:
        rule_id = record["source"]["rule"]
        if record["result"] == "fail":
            fails[rule_id].add(record["subject"]["resource"])
        elif record["result"] == "pass":
            passes[rule_id].add(record["subject"]["resource"])
        observed = record["observed_at"]
        if rule_id not in last_seen or observed > last_seen[rule_id]:
            last_seen[rule_id] = observed
        evidence_ids[rule_id].append(record["evidence_id"])

    rows = []
    for control in catalogue["annex_a"]:
        control_id = control["id"]
        rule_ids = by_iso.get(control_id, [])
        row = {
            "id": control_id,
            "title": control["title"],
            "theme": control["theme"],
            "applicability": control["applicability"],
            "owner": control.get("owner"),
            "due": control.get("due"),
            "residual": control.get("residual"),
            "justification": control.get("justification"),
            "rules": rule_ids,
            "failing_rules": [],
            "passing_rules": [],
            "last_observed_at": None,
            "evidence_ids": [],
        }
        if control["applicability"] == "not-applicable":
            row["status"] = "not-applicable"
            rows.append(row)
            continue
        if not rule_ids:
            row["status"] = "manual"
            rows.append(row)
            continue
        failing = [rule_id for rule_id in rule_ids if fails.get(rule_id)]
        passing = [rule_id for rule_id in rule_ids if passes.get(rule_id) and not fails.get(rule_id)]
        row["failing_rules"] = failing
        row["passing_rules"] = passing
        seen = [last_seen[rule_id] for rule_id in rule_ids if rule_id in last_seen]
        row["last_observed_at"] = max(seen) if seen else None
        for rule_id in rule_ids:
            row["evidence_ids"].extend(evidence_ids.get(rule_id, []))
        if failing:
            row["status"] = "automated-fail"
        elif passing:
            # Every Annex A control we automate still has an organisational
            # remainder, so a clean scan is partial rather than a full pass.
            row["status"] = "partial"
        else:
            row["status"] = "manual"
        rows.append(row)
    return rows


def status_counts(rows: list[dict]) -> dict:
    counts = {
        "automated-pass": 0,
        "automated-fail": 0,
        "partial": 0,
        "manual": 0,
        "not-applicable": 0,
    }
    for row in rows:
        counts[row["status"]] += 1
    return counts


def framework_coverage(catalogue: dict) -> dict:
    iso_rules = rules_by_iso(catalogue)
    c5: set[str] = set()
    dora: set[str] = set()
    grundschutz: set[str] = set()
    for rule in catalogue["rules"]:
        c5.update(rule.get("c5") or [])
        dora.update(rule.get("dora") or [])
        grundschutz.update(rule.get("grundschutz") or [])
    tracked = [item["id"] for item in catalogue["dora_tracked"]]
    dora_hit = [item for item in tracked if item in dora]
    c5_total = int(catalogue["c5_criteria_total"])
    return {
        "annex_a": {
            "total": len(catalogue["annex_a"]),
            "with_automated_check": len(iso_rules),
            "automation_coverage_pct": pct(len(iso_rules), len(catalogue["annex_a"])),
        },
        "c5": {
            "criteria_in_catalogue_2020": c5_total,
            "source": catalogue["c5_criteria_total_source"],
            "with_automated_check": sorted(c5),
            "coverage_pct": pct(len(c5), c5_total),
        },
        "dora": {
            "tracked": [
                {"id": item["id"], "topic": item["topic"]} for item in catalogue["dora_tracked"]
            ],
            "with_automated_check": dora_hit,
            "coverage_pct": pct(len(dora_hit), len(tracked)),
        },
        "grundschutz": {
            "modules_referenced": [
                {"id": module_id, "gloss": catalogue["grundschutz_gloss"][module_id]}
                for module_id in sorted(grundschutz)
            ],
            "note": (
                "No percentage of the full IT-Grundschutz compendium. "
                "The list is only the modules a rule in this catalogue points at."
            ),
        },
        "nis2": catalogue["nis2"],
    }


def annex_summary(rows: list[dict], catalogue: dict) -> dict:
    counts = status_counts(rows)
    coverage = framework_coverage(catalogue)
    automated = counts["partial"] + counts["automated-pass"] + counts["automated-fail"]
    return {
        "total": len(rows),
        "with_automated_check": coverage["annex_a"]["with_automated_check"],
        "automated_pass": counts["automated-pass"],
        "automated_fail": counts["automated-fail"],
        "partial": counts["partial"],
        "manual": counts["manual"],
        "not_applicable": counts["not-applicable"],
        "automation_coverage_pct": coverage["annex_a"]["automation_coverage_pct"],
        "status_sum_check": automated + counts["manual"] + counts["not-applicable"],
    }
