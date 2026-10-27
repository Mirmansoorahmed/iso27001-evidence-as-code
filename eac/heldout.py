from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

from eac.catalogue import rego_ids
from eac.collect import from_checkov, from_conftest
from eac.scanners import ScannerError, run_checkov, run_conftest
from eac.score import score_expectations

TERRAGOAT_COMMIT = "729f8da62c6a85ce4af5ad3d123de97776d954c4"
TERRAGOAT_URL = "https://github.com/bridgecrewio/terragoat.git"


def fetch_terragoat(cache: Path | None = None) -> Path:
    dest = cache or Path("/tmp") / f"eac-terragoat-{TERRAGOAT_COMMIT[:12]}"
    marker = dest / "terraform" / "azure"
    if marker.is_dir() and (dest / "LICENSE").is_file():
        return dest
    if dest.exists():
        subprocess.run(["rm", "-rf", str(dest)], check=True)
    dest.mkdir(parents=True)
    subprocess.check_call(["git", "init", str(dest)])
    subprocess.check_call(["git", "-C", str(dest), "remote", "add", "origin", TERRAGOAT_URL])
    subprocess.check_call(
        ["git", "-C", str(dest), "fetch", "--depth", "1", "origin", TERRAGOAT_COMMIT]
    )
    subprocess.check_call(["git", "-C", str(dest), "checkout", "--detach", "FETCH_HEAD"])
    return dest


def run_heldout(root: Path, catalogue: dict, *, checkov_version: str, conftest_version: str, observed_at: str) -> dict:
    expected = yaml.safe_load((root / "fixtures" / "held-out" / "terragoat-expected.yaml").read_text())
    checkout = fetch_terragoat()
    license_text = (checkout / "LICENSE").read_text(errors="replace")
    if "Apache License" not in license_text.splitlines()[0] and "Apache License" not in license_text[:400]:
        return {
            "skipped": True,
            "reason": f"TerraGoat LICENSE at {TERRAGOAT_COMMIT} is not Apache-2.0; held-out set not scored.",
        }
    azure = checkout / "terraform" / "azure"
    try:
        report = run_checkov(azure, list(expected["technical"]))
    except ScannerError as exc:
        return {"skipped": True, "reason": f"checkov failed on TerraGoat: {exc}"}
    try:
        conftest = run_conftest(azure, root / "policies")
    except ScannerError as exc:
        return {"skipped": True, "reason": f"conftest failed on TerraGoat: {exc}"}
    evidence = from_checkov(
        report,
        root=azure,
        catalogue=catalogue,
        version=checkov_version,
        observed_at=observed_at,
        prev_manifest_sha256="",
    )
    evidence.extend(
        from_conftest(
            [{"directory": azure, "result": conftest}],
            root=azure,
            catalogue=catalogue,
            version=conftest_version,
            observed_at=observed_at,
            prev_manifest_sha256="",
            rego_ids=rego_ids(catalogue),
        )
    )
    technical = score_expectations(expected, evidence, group="technical")
    nordpay = score_expectations(expected, evidence, group="nordpay")
    head = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
    return {
        "skipped": False,
        "repo": TERRAGOAT_URL,
        "commit": head,
        "expected_commit": expected["commit"],
        "license": "Apache-2.0",
        "path": "terraform/azure",
        "attribution": "TerraGoat is Bridgecrew's vulnerable-by-design Terraform, used here as a held-out set. It is not vendored.",
        "checkov_summary": report.get("summary") or {},
        "technical": technical,
        "nordpay": nordpay,
        "note": expected.get("note", ""),
    }
