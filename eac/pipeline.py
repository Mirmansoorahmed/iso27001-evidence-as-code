from __future__ import annotations

import platform
import shutil
import socket
import time
from pathlib import Path

from eac.catalogue import checkov_ids, load_catalogue, rego_ids
from eac.collect import from_checkov, from_conftest
from eac.dashboard import write_dashboard
from eac.drift import lost_controls
from eac.pack import export_pack, tar_pack
from eac.scanners import policy_directories, run_checkov, run_conftest
from eac.score import load_fixture_expectations, score_fixtures
from eac.soa import annex_summary, framework_coverage, rollup
from eac.util import GENESIS, canonical, git_commit, now_iso, repo_root, which_version


def _tool_versions() -> dict:
    checkov = which_version(["checkov", "--version"]).splitlines()[0].strip()
    conftest_raw = which_version(["conftest", "--version"])
    terraform = "not-installed"
    if shutil.which("terraform"):
        terraform = which_version(["terraform", "version"]).splitlines()[0].strip()
    return {
        "checkov": checkov,
        "conftest": conftest_raw.replace("\n", " | "),
        "terraform": terraform,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "hostname": socket.gethostname(),
    }


def _with_prev(records: list[dict], prev: str) -> list[dict]:
    updated = []
    for record in records:
        copy = dict(record)
        copy["prev_manifest_sha256"] = prev
        updated.append(copy)
    return updated


def _failed_controls(rows: list[dict]) -> list[dict]:
    failed = []
    for row in rows:
        if row["status"] != "automated-fail":
            continue
        failed.append({"control": row["id"], "title": row["title"], "rules": row["failing_rules"]})
    return failed


def run_pipeline(
    root: Path | None = None,
    out: Path | None = None,
    *,
    period: str = "2026-Q4",
    export_repeats: int = 1,
    command: str = "eac run",
) -> dict:
    root = (root or repo_root()).resolve()
    out = (out or (root / "dist" / "run")).resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    started = time.perf_counter()
    started_at = now_iso()
    catalogue = load_catalogue(root)
    tools = _tool_versions()
    checkov_version = tools["checkov"]
    conftest_version = tools["conftest"]

    scan_started = time.perf_counter()
    report = run_checkov(root, checkov_ids(catalogue))
    conftest_runs = []
    for directory in policy_directories(root):
        conftest_runs.append(
            {"directory": directory, "result": run_conftest(directory, root / "policies")}
        )
    scan_seconds = time.perf_counter() - scan_started
    observed_at = now_iso()
    evidence = from_checkov(
        report,
        root=root,
        catalogue=catalogue,
        version=checkov_version,
        observed_at=observed_at,
        prev_manifest_sha256=GENESIS,
    )
    evidence.extend(
        from_conftest(
            conftest_runs,
            root=root,
            catalogue=catalogue,
            version=conftest_version,
            observed_at=observed_at,
            prev_manifest_sha256=GENESIS,
            rego_ids=rego_ids(catalogue),
        )
    )
    evidence.sort(key=lambda item: (item["subject"]["file"], item["source"]["rule"], item["subject"]["resource"], item["result"]))

    soa = rollup(catalogue, evidence, "lz")
    annex = annex_summary(soa, catalogue)
    coverage = framework_coverage(catalogue)
    fixtures = score_fixtures(load_fixture_expectations(root), evidence, rego_ids=rego_ids(catalogue))
    broken = root / "fixtures" / "drift" / "broken" / "main.tf"
    drift = lost_controls(
        catalogue,
        evidence,
        evidence,
        baseline_scope="fixtures/drift/baseline",
        candidate_scope="fixtures/drift/broken",
        commit=git_commit(broken, root),
        candidate_file="fixtures/drift/broken/main.tf",
    )
    preview_rows = rollup(catalogue, evidence, "fixtures/pr-preview")
    pr_preview = {
        "path": "fixtures/pr-preview",
        "note": "fixtures/pr-preview turns anonymous blob access on and drops TLS to 1.0. It is the stand-in for a bad pull request.",
        "failed": _failed_controls(preview_rows),
    }
    lz_failures = [
        record
        for record in evidence
        if record["result"] == "fail" and (record["subject"]["file"] == "lz" or record["subject"]["file"].startswith("lz/"))
    ]
    catalogue_files = {
        "rules.yaml": (root / "catalog" / "rules.yaml").read_bytes(),
        "annex_a.yaml": (root / "catalog" / "annex_a.yaml").read_bytes(),
    }
    summary_core = {
        "produced_by": {
            "command": command,
            "started_at": started_at,
            "python": tools["python"],
            "checkov": tools["checkov"],
            "conftest": tools["conftest"],
            "terraform": tools["terraform"],
            "platform": tools["platform"],
            "hostname": tools["hostname"],
        },
        "catalogue_version": catalogue["version"],
        "scope": "lz/",
        "annex_a": annex,
        "c5": {
            "criteria_in_catalogue_2020": coverage["c5"]["criteria_in_catalogue_2020"],
            "source": coverage["c5"]["source"],
            "with_automated_check": len(coverage["c5"]["with_automated_check"]),
            "ids": coverage["c5"]["with_automated_check"],
            "coverage_pct": coverage["c5"]["coverage_pct"],
        },
        "dora": {
            "tracked": [item["id"] for item in coverage["dora"]["tracked"]],
            "with_automated_check": coverage["dora"]["with_automated_check"],
            "coverage_pct": coverage["dora"]["coverage_pct"],
        },
        "grundschutz": {
            "modules_referenced": [item["id"] for item in coverage["grundschutz"]["modules_referenced"]],
            "note": coverage["grundschutz"]["note"],
        },
        "nis2": coverage["nis2"],
        "fixtures": {key: value for key, value in fixtures.items() if key != "fixtures"},
        "lz_failure_count": len(lz_failures),
        "pr_preview_failed_controls": [item["control"] for item in pr_preview["failed"]],
        "drift_lost_controls": [item["control"] for item in drift["lost"]],
        "drift_commit": drift["commit"],
        "checkov_summary": report.get("summary") or {},
        "scan_seconds": round(scan_seconds, 4),
    }

    def _export(records: list[dict], folder: Path, prev: str, previous: bytes | None, created_at: str) -> dict:
        return export_pack(
            folder,
            period=period,
            created_at=created_at,
            catalogue_version=catalogue["version"],
            evidence=records,
            soa=soa,
            summary=summary_core,
            drift=drift,
            fixture_score=fixtures,
            catalogue_files=catalogue_files,
            prev_manifest_sha256=prev,
            previous_manifest=previous,
        )

    pack_created = observed_at
    genesis = _export(evidence, out / "pack-genesis", GENESIS, None, pack_created)
    linked = _with_prev(evidence, genesis["manifest_sha256"])
    samples = []
    latest = None
    repeats = max(1, export_repeats)
    for _ in range(repeats):
        tick = time.perf_counter()
        latest = _export(linked, out / "pack", genesis["manifest_sha256"], genesis["manifest_bytes"], pack_created)
        samples.append(time.perf_counter() - tick)
    assert latest is not None
    ordered = sorted(samples)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        median = ordered[mid]
    else:
        median = (ordered[mid - 1] + ordered[mid]) / 2
    # Timing stays outside the hashed pack. Putting the stopwatch into the
    # manifest would change the bytes being timed.
    summary = dict(summary_core)
    summary["export"] = {
        "repeats": repeats,
        "seconds": [round(sample, 6) for sample in samples],
        "median_seconds": round(median, 6),
        "min_seconds": round(min(samples), 6),
        "max_seconds": round(max(samples), 6),
        "what": "Time to build the auditor pack from an already collected evidence set. The clock inside the pack is fixed across repeats so the samples package the same bytes.",
    }
    summary["pipeline_seconds"] = round(time.perf_counter() - started, 4)
    summary["produced_by"] = dict(summary_core["produced_by"])
    summary["produced_by"]["finished_at"] = now_iso()
    summary["manifest_sha256"] = latest["manifest_sha256"]
    summary["prev_manifest_sha256"] = genesis["manifest_sha256"]
    tar_pack(out / "pack", out / f"nordpay-evidence-{period}.tar.gz")

    payload = {
        "period": period,
        "observed_at": observed_at,
        "catalogue_version": catalogue["version"],
        "counts": {
            "automated-pass": annex["automated_pass"],
            "automated-fail": annex["automated_fail"],
            "partial": annex["partial"],
            "manual": annex["manual"],
            "not-applicable": annex["not_applicable"],
        },
        "annex": annex,
        "c5": coverage["c5"],
        "dora": coverage["dora"],
        "rows": soa,
        "pr_preview": pr_preview,
        "drift": drift,
        "fixtures": summary_core["fixtures"],
        "manifest_sha256": latest["manifest_sha256"],
        "prev_manifest_sha256": genesis["manifest_sha256"],
        "tools": {"checkov": tools["checkov"], "conftest": tools["conftest"]},
    }
    write_dashboard(out / "dashboard", payload)
    (out / "evidence.json").write_bytes(canonical(linked))
    (out / "soa.json").write_bytes(canonical(soa))
    (out / "fixture-score.json").write_bytes(canonical(fixtures))
    (out / "drift.json").write_bytes(canonical(drift))
    (out / "summary.json").write_bytes(canonical(summary))
    (out / "checkov-summary.json").write_bytes(canonical(report.get("summary") or {}))
    chain = out / "chain"
    chain.mkdir()
    (chain / "genesis-manifest.json").write_bytes(genesis["manifest_bytes"])
    (chain / "latest-manifest.json").write_bytes(latest["manifest_bytes"])
    (chain / "latest.sha256").write_text(latest["manifest_sha256"] + "\n")
    return {
        "out": out,
        "summary": summary,
        "soa": soa,
        "evidence": linked,
        "fixtures": fixtures,
        "drift": drift,
        "pr_preview": pr_preview,
        "tools": tools,
        "catalogue": catalogue,
        "observed_at": observed_at,
        "pack": out / "pack",
        "genesis_manifest": genesis["manifest_bytes"],
        "latest_manifest_sha256": latest["manifest_sha256"],
    }


def median_note(summary: dict) -> str:
    export = summary["export"]
    return (
        f"{export['median_seconds']}s median over {export['repeats']} pack builds "
        f"(min {export['min_seconds']}s, max {export['max_seconds']}s)"
    )
