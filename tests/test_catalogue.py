from pathlib import Path

from eac.catalogue import load_catalogue, rego_ids

ROOT = Path(__file__).resolve().parents[1]


def annex_ids():
    ids = [f"A.5.{i}" for i in range(1, 38)]
    ids += [f"A.6.{i}" for i in range(1, 9)]
    ids += [f"A.7.{i}" for i in range(1, 15)]
    ids += [f"A.8.{i}" for i in range(1, 35)]
    assert len(ids) == 93
    return ids


def test_annex_a_is_the_93_controls():
    catalogue = load_catalogue(ROOT)
    found = [control["id"] for control in catalogue["annex_a"]]
    assert found == annex_ids()
    assert len({control["title"] for control in catalogue["annex_a"]}) == 93


def test_titles_stay_short():
    catalogue = load_catalogue(ROOT)
    for control in catalogue["annex_a"]:
        assert len(control["title"]) < 120
        assert "\n" not in control["title"]


def test_rule_refs_exist():
    catalogue = load_catalogue(ROOT)
    iso = {control["id"] for control in catalogue["annex_a"]}
    c5 = set(catalogue["c5_gloss"])
    grundschutz = set(catalogue["grundschutz_gloss"])
    dora = {item["id"] for item in catalogue["dora_tracked"]}
    for rule in catalogue["rules"]:
        assert set(rule["iso"]) <= iso
        assert set(rule.get("c5") or []) <= c5
        assert set(rule.get("grundschutz") or []) <= grundschutz
        assert set(rule.get("dora") or []) <= dora
        for tag in rule.get("nis2") or []:
            assert tag == catalogue["nis2"]["tag"]


def test_rego_rule_ids_are_emitted_by_the_policies():
    catalogue = load_catalogue(ROOT)
    source = "\n".join(path.read_text() for path in (ROOT / "policies").glob("*.rego"))
    for rule_id in rego_ids(catalogue):
        assert rule_id in source


def test_standard_text_is_not_copied():
    banned = [
        "The cloud service provider operates an information security management system",
        "financial entities shall have in place an internal governance and control framework",
    ]
    blobs = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in path.parts for part in (".git", ".terraform", "dist", "__pycache__", "tests")):
            continue
        if path.suffix.lower() not in {".py", ".yaml", ".yml", ".md", ".rego", ".tf", ".html", ".j2"}:
            continue
        blobs.append(path.read_text(errors="ignore"))
    text = "\n".join(blobs)
    for phrase in banned:
        assert phrase not in text
