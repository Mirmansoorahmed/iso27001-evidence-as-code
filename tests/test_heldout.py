from pathlib import Path

from eac.catalogue import load_catalogue
from eac.heldout import TERRAGOAT_COMMIT, run_heldout

ROOT = Path(__file__).resolve().parents[1]


def test_terragoat_held_out_matches_the_hcl_reading():
    catalogue = load_catalogue(ROOT)
    result = run_heldout(
        ROOT,
        catalogue,
        checkov_version="3.2.449",
        conftest_version="test",
        observed_at="2026-10-27T00:00:00Z",
    )
    assert result["skipped"] is False, result.get("reason")
    assert result["commit"] == TERRAGOAT_COMMIT
    assert result["license"] == "Apache-2.0"
    technical = result["technical"]
    # CKV_AZURE_3 treats a missing enable_https_traffic_only as a pass.
    # TerraGoat never sets it. That is a false negative of the adopted check.
    assert "CKV_AZURE_3" in technical["fn_rules"]
    assert technical["false_positive"] == 0
    nordpay = result["nordpay"]
    assert nordpay["false_positive"] == 0
    assert nordpay["false_negative"] == 0
    assert nordpay["true_positive"] >= 1
