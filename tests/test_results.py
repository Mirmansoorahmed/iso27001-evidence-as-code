import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "results" / "summary.json"


@pytest.mark.skipif(not SUMMARY.is_file(), reason="measurement snapshot is written by eac demo")
def test_readme_and_demo_quote_the_measured_numbers():
    summary = json.loads(SUMMARY.read_text())
    readme = (ROOT / "README.md").read_text()
    demo = (ROOT / "docs" / "DEMO.md").read_text()
    annex = summary["annex_a"]
    fixtures = summary["fixtures"]
    export = summary["export"]
    technical = summary["terragoat"]["technical"]
    needles = [
        f"{annex['with_automated_check']} of {annex['total']}",
        annex["automation_coverage_pct"],
        str(annex["partial"]),
        str(annex["manual"]),
        str(annex["not_applicable"]),
        str(fixtures["true_positive"]),
        str(fixtures["false_positive"]),
        str(fixtures["false_negative"]),
        str(fixtures["true_negative"]),
        str(export["median_seconds"]),
        str(technical["false_negative"]),
        summary["c5"]["coverage_pct"],
        summary["dora"]["coverage_pct"],
    ]
    for needle in needles:
        assert needle in readme, needle
        assert needle in demo, needle


@pytest.mark.skipif(not SUMMARY.is_file(), reason="measurement snapshot is written by eac demo")
def test_summary_arithmetic_matches_the_file():
    summary = json.loads(SUMMARY.read_text())
    annex = summary["annex_a"]
    assert annex["total"] == 93
    assert (
        annex["automated_pass"]
        + annex["automated_fail"]
        + annex["partial"]
        + annex["manual"]
        + annex["not_applicable"]
    ) == 93
    assert summary["fixtures"]["false_positive"] == 0
    assert summary["fixtures"]["false_negative"] == 0
    assert "CKV_AZURE_3" in summary["terragoat"]["technical"]["fn_rules"]
