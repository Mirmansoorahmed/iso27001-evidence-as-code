from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def render_html(payload: dict) -> str:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("dashboard.html.j2")
    return template.render(payload=payload)


def render_markdown(payload: dict) -> str:
    lines = [
        f"# NordPay statement of applicability ({payload['period']})",
        "",
        "NordPay GmbH is fictional. Partial means the automated checks passed and the rest of the control is manual.",
        "",
        f"Automated checks: {payload['annex']['with_automated_check']} of {payload['annex']['total']} ({payload['annex']['automation_coverage_pct']}%).",
        "",
        "| Id | Status | Title |",
        "| --- | --- | --- |",
    ]
    for row in payload["rows"]:
        title = row["title"].replace("|", "/")
        lines.append(f"| {row['id']} | {row['status']} | {title} |")
    lines.append("")
    if payload["drift"]["lost"]:
        lines.append("## Drift")
        lines.append("")
        for item in payload["drift"]["lost"]:
            lines.append(
                f"- {item['control']} lost evidence at `{item['commit']}` via {', '.join(item['rules'])}."
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def write_dashboard(directory: Path, payload: dict) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "index.html").write_text(render_html(payload))
    (directory / "soa.md").write_text(render_markdown(payload))
    safe = json.dumps(payload, ensure_ascii=True)
    (directory / "payload.json").write_text(safe + "\n")
