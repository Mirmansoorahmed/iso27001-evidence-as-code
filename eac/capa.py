from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from collections.abc import Callable

from eac.util import canonical, sha256_bytes


def fingerprint(record: dict) -> str:
    raw = canonical(
        {
            "rule": record["source"]["rule"],
            "resource": record["subject"]["resource"],
            "file": record["subject"]["file"],
        }
    )
    return sha256_bytes(raw)[:16]


def capa_status() -> dict | None:
    if os.environ.get("EAC_CAPA") != "1":
        return {"skipped": True, "reason": "EAC_CAPA is not 1"}
    if not os.environ.get("GITHUB_TOKEN"):
        return {"skipped": True, "reason": "GITHUB_TOKEN is not set"}
    if not os.environ.get("GITHUB_REPOSITORY"):
        return {"skipped": True, "reason": "GITHUB_REPOSITORY is not set"}
    return None


def _request(method: str, url: str, token: str, body: dict | None = None) -> dict:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "nordpay-eac",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = response.read().decode()
    if not payload:
        return {}
    return json.loads(payload)


def reconcile(
    evidence: list[dict],
    *,
    transport: Callable[[str, str, str, dict | None], dict] | None = None,
) -> dict:
    skipped = capa_status()
    if skipped and transport is None:
        return skipped
    token = os.environ.get("GITHUB_TOKEN", "test-token")
    repo = os.environ.get("GITHUB_REPOSITORY", "example/example")
    call = transport or _request
    failures = [record for record in evidence if record["result"] == "fail"]
    open_fps = {fingerprint(record): record for record in failures}
    actions = []
    already = _open_corrective_actions(call, token, repo)
    known = {item["fingerprint"]: item for item in already}
    for fp, record in sorted(open_fps.items()):
        if fp in known:
            actions.append({"action": "exists", "fingerprint": fp, "number": known[fp].get("number")})
            continue
        created = call(
            "POST",
            f"https://api.github.com/repos/{repo}/issues",
            token,
            _issue_body(record, fp),
        )
        actions.append({"action": "opened", "fingerprint": fp, "number": created.get("number")})
    for item in already:
        fp = item["fingerprint"]
        if fp in open_fps or not item.get("number"):
            continue
        number = item["number"]
        call(
            "POST",
            f"https://api.github.com/repos/{repo}/issues/{number}/comments",
            token,
            {"body": f"Closing. A later scan no longer records a failure for fingerprint `{fp}`."},
        )
        call(
            "PATCH",
            f"https://api.github.com/repos/{repo}/issues/{number}",
            token,
            {"state": "closed", "state_reason": "completed"},
        )
        actions.append({"action": "closed", "fingerprint": fp, "number": number})
    return {"skipped": False, "actions": actions}


def _open_corrective_actions(call, token: str, repo: str) -> list[dict]:
    query = urllib.parse.quote(f"repo:{repo} is:issue is:open label:corrective-action")
    found = call("GET", f"https://api.github.com/search/issues?q={query}&per_page=100", token, None)
    items = found.get("items") or []
    parsed = []
    for item in items:
        body = item.get("body") or ""
        fp = ""
        for line in body.splitlines():
            if line.startswith("fingerprint:"):
                fp = line.split(":", 1)[1].strip()
                break
        parsed.append({"number": item.get("number"), "fingerprint": fp, "state": item.get("state")})
    return parsed


def _issue_body(record: dict, fp: str) -> dict:
    controls = ", ".join(
        ref["id"] for ref in record["control_refs"] if ref["framework"] == "iso27001-2022"
    )
    return {
        "title": f"[{controls or record['source']['rule']}] {record['source']['rule']} failed",
        "body": (
            f"fingerprint:{fp}\n\n"
            f"Rule: `{record['source']['rule']}` ({record['source']['tool']})\n"
            f"Resource: `{record['subject']['resource']}`\n"
            f"File: `{record['subject']['file']}`\n"
            f"Commit: `{record['subject']['commit']}`\n"
            f"Evidence: `{record['evidence_id']}`\n\n"
            f"{record['detail']}\n\n"
            "This issue is a corrective action from the evidence pipeline. "
            "It is not a statement that a control has failed an audit.\n"
        ),
        "labels": ["corrective-action"],
    }
