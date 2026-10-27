from __future__ import annotations

from eac.catalogue import rules_by_iso
from eac.soa import rollup


def lost_controls(
    catalogue: dict,
    baseline: list[dict],
    candidate: list[dict],
    *,
    baseline_scope: str,
    candidate_scope: str,
    commit: str,
    candidate_file: str,
) -> dict:
    before = {row["id"]: row for row in rollup(catalogue, baseline, baseline_scope)}
    after = {row["id"]: row for row in rollup(catalogue, candidate, candidate_scope)}
    by_iso = rules_by_iso(catalogue)
    lost = []
    for control_id, row in after.items():
        if row["status"] != "automated-fail":
            continue
        previous = before.get(control_id)
        if previous is None or previous["status"] == "automated-fail":
            continue
        rules = [rule_id for rule_id in by_iso.get(control_id, []) if rule_id in row["failing_rules"]]
        lost.append(
            {
                "control": control_id,
                "title": row["title"],
                "rules": rules,
                "commit": commit,
                "file": candidate_file,
            }
        )
    lost.sort(key=lambda item: item["control"])
    return {
        "mode": "offline-fixture",
        "note": (
            "Simulated drift. Nothing was changed in a cloud account. "
            "The broken fixture is a second copy of the storage account with TLS lowered, "
            "and the commit is the commit that introduced that file."
        ),
        "baseline": baseline_scope,
        "candidate": candidate_scope,
        "commit": commit,
        "lost": lost,
    }
