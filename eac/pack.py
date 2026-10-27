from __future__ import annotations

import shutil
import tarfile
from pathlib import Path

from eac.util import canonical, sha256_bytes

VERIFY_SH = Path(__file__).resolve().parent / "templates" / "verify.sh"


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def export_pack(
    dest: Path,
    *,
    period: str,
    created_at: str,
    catalogue_version: str,
    evidence: list[dict],
    soa: list[dict],
    summary: dict,
    drift: dict,
    fixture_score: dict,
    catalogue_files: dict[str, bytes],
    prev_manifest_sha256: str,
    previous_manifest: bytes | None,
) -> dict:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    _write(dest / "evidence" / "records.json", canonical(evidence))
    _write(dest / "soa" / "soa.json", canonical(soa))
    _write(dest / "soa" / "summary.json", canonical(summary))
    _write(dest / "drift" / "drift.json", canonical(drift))
    _write(dest / "fixtures" / "fixture-score.json", canonical(fixture_score))
    for name, payload in sorted(catalogue_files.items()):
        _write(dest / "catalogue" / name, payload)
    readme = (
        "NordPay GmbH evidence pack (fictional company).\n"
        "Verify with ./verify.sh from this directory. It uses sha256sum and jq only.\n"
        "A passing verification shows the files match the manifest. It is not a certification.\n"
        f"Period: {period}\n"
        f"Catalogue: {catalogue_version}\n"
        f"Created: {created_at}\n"
        "Cosign signing is optional and off unless EAC_COSIGN=1.\n"
    ).encode()
    _write(dest / "README.txt", readme)
    shutil.copyfile(VERIFY_SH, dest / "verify.sh")
    (dest / "verify.sh").chmod(0o755)
    if previous_manifest is not None:
        _write(dest / "previous" / "MANIFEST.json", previous_manifest)

    files = []
    for path in sorted(p for p in dest.rglob("*") if p.is_file()):
        rel = path.relative_to(dest).as_posix()
        if rel in {"MANIFEST.json", "MANIFEST.sha256"}:
            continue
        files.append({"path": rel, "sha256": sha256_bytes(path.read_bytes())})
    manifest = {
        "manifest_version": 1,
        "period": period,
        "created_at": created_at,
        "catalogue_version": catalogue_version,
        "prev_manifest_sha256": prev_manifest_sha256,
        "files": files,
    }
    manifest_bytes = canonical(manifest)
    _write(dest / "MANIFEST.json", manifest_bytes)
    digest = sha256_bytes(manifest_bytes)
    _write(dest / "MANIFEST.sha256", f"{digest}  MANIFEST.json\n".encode())
    return {"directory": str(dest), "manifest_sha256": digest, "manifest_bytes": manifest_bytes}


def tar_pack(directory: Path, archive: Path) -> None:
    archive.parent.mkdir(parents=True, exist_ok=True)
    if archive.exists():
        archive.unlink()
    with tarfile.open(archive, "w:gz") as handle:
        handle.add(directory, arcname=directory.name)
