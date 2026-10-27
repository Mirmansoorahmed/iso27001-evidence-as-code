import subprocess
from pathlib import Path

import pytest

from eac.pipeline import run_pipeline

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def pipeline(tmp_path_factory):
    out = tmp_path_factory.mktemp("pipeline")
    return run_pipeline(root=ROOT, out=out, export_repeats=2)


def test_landing_zone_has_no_failures(pipeline):
    assert pipeline["summary"]["lz_failure_count"] == 0


def test_soa_covers_every_annex_a_control(pipeline):
    summary = pipeline["summary"]["annex_a"]
    assert summary["total"] == 93
    assert summary["status_sum_check"] == 93
    counted = (
        summary["automated_pass"]
        + summary["automated_fail"]
        + summary["partial"]
        + summary["manual"]
        + summary["not_applicable"]
    )
    assert counted == 93
    assert summary["automated_pass"] == 0
    assert summary["automated_fail"] == 0
    assert summary["not_applicable"] == 2
    assert summary["partial"] == summary["with_automated_check"]
    assert summary["partial"] + summary["manual"] + summary["not_applicable"] == 93


def test_own_fixtures_match_their_labels(pipeline):
    fixtures = pipeline["fixtures"]
    assert fixtures["misconfigured"] == 22
    assert fixtures["negative_controls"] == 1
    assert fixtures["false_positive"] == 0
    assert fixtures["false_negative"] == 0
    assert fixtures["true_positive"] > 0
    assert fixtures["true_negative"] > 0


def test_drift_names_the_controls_that_broke(pipeline):
    lost = {item["control"] for item in pipeline["drift"]["lost"]}
    assert lost == {"A.8.9", "A.8.24"}


def test_pr_preview_fails_the_controls_the_change_touches(pipeline):
    failed = set(pipeline["summary"]["pr_preview_failed_controls"])
    assert failed == {"A.5.15", "A.8.3", "A.8.9", "A.8.24"}


def test_pack_verifies_and_rejects_a_tamper(pipeline):
    pack = pipeline["pack"]
    subprocess.check_call(["sh", "./verify.sh"], cwd=pack)
    records = pack / "evidence" / "records.json"
    original = records.read_bytes()
    try:
        mutated = bytearray(original)
        mutated[-2] = (mutated[-2] + 1) % 256
        records.write_bytes(bytes(mutated))
        proc = subprocess.run(["sh", "./verify.sh"], cwd=pack, capture_output=True, text=True)
        assert proc.returncode != 0
    finally:
        records.write_bytes(original)
    subprocess.check_call(["sh", "./verify.sh"], cwd=pack)
    previous = (pack / "previous" / "MANIFEST.json").read_bytes()
    genesis = pipeline["genesis_manifest"]
    assert previous == genesis
    assert pipeline["summary"]["prev_manifest_sha256"]
    assert pipeline["summary"]["manifest_sha256"] != pipeline["summary"]["prev_manifest_sha256"]


def test_verify_script_limits_itself_to_sha256sum_and_jq():
    script = (ROOT / "eac" / "templates" / "verify.sh").read_text()
    for banned in ("python", "openssl", "cosign", "awk", "sha256("):
        assert banned not in script
    assert "sha256sum" in script
    assert "jq" in script
