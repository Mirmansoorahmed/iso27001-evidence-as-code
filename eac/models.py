from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ControlRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    framework: str
    id: str


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: str
    version: str
    rule: str
    mode: Literal["offline", "live"] = "offline"


class Subject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource: str
    file: str
    commit: str


class EvidenceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    control_refs: list[ControlRef]
    source: Source
    subject: Subject
    result: Literal["pass", "fail", "error"]
    observed_at: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    prev_manifest_sha256: str
    detail: str
