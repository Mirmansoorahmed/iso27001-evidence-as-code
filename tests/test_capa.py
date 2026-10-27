import json
import os

from eac.capa import reconcile


def _record(result, rule="CKV_AZURE_44", resource="azurerm_storage_account.payments"):
    return {
        "evidence_id": "00000000-0000-0000-0000-000000000001",
        "control_refs": [{"framework": "iso27001-2022", "id": "A.8.24"}],
        "source": {"tool": "checkov", "version": "3.2.449", "rule": rule, "mode": "offline"},
        "subject": {"resource": resource, "file": "lz/storage.tf", "commit": "abc"},
        "result": result,
        "observed_at": "2026-10-27T00:00:00Z",
        "sha256": "a" * 64,
        "prev_manifest_sha256": "",
        "detail": "tls",
    }


def test_capa_skips_without_the_flag(monkeypatch):
    monkeypatch.delenv("EAC_CAPA", raising=False)
    outcome = reconcile([_record("fail")])
    assert outcome["skipped"] is True
    assert "EAC_CAPA" in outcome["reason"]


def test_capa_skips_without_a_token(monkeypatch):
    monkeypatch.setenv("EAC_CAPA", "1")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_REPOSITORY", "example/example")
    outcome = reconcile([_record("fail")])
    assert outcome["skipped"] is True
    assert "GITHUB_TOKEN" in outcome["reason"]


def test_capa_opens_and_closes_with_a_fake_github(monkeypatch):
    monkeypatch.setenv("EAC_CAPA", "1")
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setenv("GITHUB_REPOSITORY", "example/example")
    calls = []

    def transport(method, url, token, body):
        calls.append((method, url, body))
        if method == "GET":
            return {
                "items": [
                    {
                        "number": 7,
                        "state": "open",
                        "body": "fingerprint:closed-me\n",
                    }
                ]
            }
        if method == "POST" and url.endswith("/issues"):
            return {"number": 9}
        return {}

    outcome = reconcile([_record("fail")], transport=transport)
    assert outcome["skipped"] is False
    actions = {item["action"] for item in outcome["actions"]}
    assert "opened" in actions
    assert "closed" in actions
    opened = next(body for method, url, body in calls if method == "POST" and url.endswith("/issues"))
    assert "fingerprint:" in opened["body"]
    assert "A.8.24" in opened["title"]
    assert json.dumps(opened)
    assert os.environ["EAC_CAPA"] == "1"
