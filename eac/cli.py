from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from eac.capa import reconcile
from eac.heldout import run_heldout
from eac.pipeline import run_pipeline
from eac.util import canonical, repo_root


def _print_transcript(summary: dict, heldout: dict | None) -> None:
    annex = summary["annex_a"]
    fixtures = summary["fixtures"]
    export = summary["export"]
    print("NordPay evidence pipeline (fictional firm, offline).")
    print(f"Landing zone failures: {summary['lz_failure_count']}")
    print(
        f"Annex A: {annex['with_automated_check']} of {annex['total']} have an automated check "
        f"({annex['automation_coverage_pct']}%). "
        f"partial {annex['partial']}, manual {annex['manual']}, "
        f"not applicable {annex['not_applicable']}, "
        f"automated-pass {annex['automated_pass']}, automated-fail {annex['automated_fail']}."
    )
    print(
        f"C5:2020: {summary['c5']['with_automated_check']} of {summary['c5']['criteria_in_catalogue_2020']} "
        f"({summary['c5']['coverage_pct']}%). "
        f"DORA tracked slice: {len(summary['dora']['with_automated_check'])} of {len(summary['dora']['tracked'])} "
        f"({summary['dora']['coverage_pct']}%)."
    )
    print(
        f"Own fixtures: TP {fixtures['true_positive']} FP {fixtures['false_positive']} "
        f"FN {fixtures['false_negative']} TN {fixtures['true_negative']}."
    )
    lost = ", ".join(summary["drift_lost_controls"]) or "(none)"
    print(f"Drift, controls that lost evidence: {lost} at {summary['drift_commit']}.")
    print(
        f"Auditor pack: median {export['median_seconds']}s over {export['repeats']} builds "
        f"(min {export['min_seconds']}s, max {export['max_seconds']}s)."
    )
    print(f"Pipeline wall clock, including the scan: {summary['pipeline_seconds']}s.")
    if heldout:
        if heldout.get("skipped"):
            print(f"TerraGoat held-out skipped: {heldout['reason']}")
        else:
            technical = heldout["technical"]
            nordpay = heldout["nordpay"]
            print(
                f"TerraGoat {heldout['commit'][:12]} technical: "
                f"TP {technical['true_positive']} FP {technical['false_positive']} "
                f"FN {technical['false_negative']} TN {technical['true_negative']} "
                f"(FN rules: {', '.join(technical['fn_rules']) or 'none'})."
            )
            print(
                f"TerraGoat NordPay-only policies: "
                f"TP {nordpay['true_positive']} FP {nordpay['false_positive']} "
                f"FN {nordpay['false_negative']} TN {nordpay['true_negative']}."
            )


def _tamper_demo(pack: Path) -> None:
    print("Verifying the pack, then flipping one byte.")
    subprocess.check_call(["sh", "./verify.sh"], cwd=pack)
    records = pack / "evidence" / "records.json"
    original = records.read_bytes()
    try:
        mutated = bytearray(original)
        mutated[-2] = (mutated[-2] + 1) % 256
        records.write_bytes(bytes(mutated))
        proc = subprocess.run(["sh", "./verify.sh"], cwd=pack, capture_output=True, text=True)
        if proc.returncode == 0:
            raise SystemExit("tamper check failed open: verify.sh accepted a changed evidence file")
        print(f"Tampered pack rejected, verify.sh exit {proc.returncode}.")
    finally:
        records.write_bytes(original)
    subprocess.check_call(["sh", "./verify.sh"], cwd=pack)


def _write_results(root: Path, result: dict, heldout: dict) -> None:
    dest = root / "results"
    dest.mkdir(exist_ok=True)
    mapping = {
        "summary.json": result["summary"],
        "soa.json": result["soa"],
        "fixture-score.json": result["fixtures"],
        "drift.json": result["drift"],
        "terragoat.json": heldout,
        "evidence.json": result["evidence"],
    }
    # summary in memory may not yet include terragoat; attach a short pointer
    summary = dict(result["summary"])
    if not heldout.get("skipped"):
        summary["terragoat"] = {
            "commit": heldout["commit"],
            "technical": {
                key: heldout["technical"][key]
                for key in ("true_positive", "false_positive", "false_negative", "true_negative", "fn_rules", "fp_rules")
            },
            "nordpay": {
                key: heldout["nordpay"][key]
                for key in ("true_positive", "false_positive", "false_negative", "true_negative", "fn_rules", "fp_rules")
            },
        }
    else:
        summary["terragoat"] = {"skipped": True, "reason": heldout.get("reason")}
    mapping["summary.json"] = summary
    for name, payload in mapping.items():
        (dest / name).write_bytes(canonical(payload))
    chain = dest / "chain"
    chain.mkdir(exist_ok=True)
    shutil.copyfile(result["out"] / "chain" / "genesis-manifest.json", chain / "genesis-manifest.json")
    shutil.copyfile(result["out"] / "chain" / "latest-manifest.json", chain / "latest-manifest.json")
    shutil.copyfile(result["out"] / "chain" / "latest.sha256", chain / "latest.sha256")
    dashboard = root / "dashboard"
    if dashboard.exists():
        shutil.rmtree(dashboard)
    shutil.copytree(result["out"] / "dashboard", dashboard)
    result["summary"] = summary


def cmd_run(args: argparse.Namespace) -> int:
    result = run_pipeline(
        out=Path(args.out) if args.out else None,
        period=args.period,
        export_repeats=args.repeats,
        command="eac run",
    )
    print(json.dumps({"out": str(result["out"]), "lz_failures": result["summary"]["lz_failure_count"]}, indent=2))
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    root = repo_root()
    result = run_pipeline(
        root=root,
        out=root / "dist" / "demo",
        period=args.period,
        export_repeats=args.repeats,
        command="eac demo",
    )
    heldout = run_heldout(
        root,
        result["catalogue"],
        checkov_version=result["tools"]["checkov"],
        conftest_version=result["tools"]["conftest"],
        observed_at=result["observed_at"],
    )
    _write_results(root, result, heldout)
    _print_transcript(result["summary"], heldout)
    _tamper_demo(result["pack"])
    print(f"Dashboard: {root / 'dashboard' / 'index.html'}")
    print(f"Pack: {result['out'] / ('nordpay-evidence-' + args.period + '.tar.gz')}")
    print(f"Numbers: {root / 'results' / 'summary.json'}")
    return 0


def cmd_capa(args: argparse.Namespace) -> int:
    evidence_path = Path(args.evidence)
    evidence = json.loads(evidence_path.read_text())
    outcome = reconcile(evidence)
    print(json.dumps(outcome, indent=2))
    return 0


def cmd_sign(args: argparse.Namespace) -> int:
    import os

    if os.environ.get("EAC_COSIGN") != "1":
        print(json.dumps({"skipped": True, "reason": "EAC_COSIGN is not 1"}))
        return 0
    if shutil.which("cosign") is None:
        print(json.dumps({"skipped": True, "reason": "cosign is not installed"}))
        return 0
    manifest = Path(args.manifest)
    bundle = manifest.with_suffix(".bundle")
    proc = subprocess.run(
        ["cosign", "sign-blob", "--yes", "--bundle", str(bundle), str(manifest)],
        check=False,
    )
    return proc.returncode


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="eac", description="NordPay offline evidence pipeline")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="scan, roll up and export")
    run.add_argument("--out")
    run.add_argument("--period", default="2026-Q4")
    run.add_argument("--repeats", type=int, default=1)
    run.set_defaults(func=cmd_run)

    demo = sub.add_parser("demo", help="measure, write results/ and show verify/tamper")
    demo.add_argument("--period", default="2026-Q4")
    demo.add_argument("--repeats", type=int, default=10)
    demo.set_defaults(func=cmd_demo)

    capa = sub.add_parser("capa", help="open or close corrective-action issues when EAC_CAPA=1")
    capa.add_argument("--evidence", required=True)
    capa.set_defaults(func=cmd_capa)

    sign = sub.add_parser("sign", help="optional cosign sign-blob; skipped unless EAC_COSIGN=1")
    sign.add_argument("--manifest", required=True)
    sign.set_defaults(func=cmd_sign)

    args = parser.parse_args(argv)
    try:
        code = args.func(args)
    except subprocess.CalledProcessError as exc:
        print(exc, file=sys.stderr)
        code = exc.returncode or 1
    raise SystemExit(code)
