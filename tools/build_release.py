#!/usr/bin/env python3
"""Assemble the v1.0 release candidate: release/photodeg-bench-v<version>/ plus a zip and a manifest.

Contents: the benchmark table, curated records, evidence and QA-flag logs, screening decisions and log,
rules, verification audit trail (deterministic results, blind comparison, adjudications), QA report,
exceptions, stats, figures, documentation, citation and license files, and machine-readable release
metadata. MANIFEST.json lists every file with its size and SHA-256. Full-text XML is not included
(article licenses vary); PROVENANCE.txt records how to re-fetch and check each file.

Usage: python tools/build_release.py --version 1.0
"""
import argparse
import datetime as dt
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FILES = [
    "data/processed/photodeg_bench_v{v}.csv", "data/curated/records.csv", "data/curated/evidence.csv",
    "data/curated/qa_flags.csv", "data/curated/rejected_records.csv", "data/curated/screening.csv",
    "data/curated/screening_log.csv", "data/processed/harmonization_log.csv", "data/processed/qa_report.txt",
    "data/processed/exceptions.csv", "data/processed/validation_report.txt", "data/processed/corpus.csv",
    "data/raw/PROVENANCE.txt", "data/curated/verification/deterministic.jsonl",
    "data/curated/verification/blind_comparison.csv", "data/curated/verification/adjudications.csv",
    "data/curated/verification/adjudication_queue.csv", "rules/harmonization.yaml", "config/search.yaml",
    "paper/stats.json", "README.md", "LICENSE", "CITATION.cff", "AUTHORS.json", "CHANGELOG.md",
    "docs/CODEBOOK.md", "docs/VOCABULARIES.md", "docs/ELIGIBILITY.md", "docs/EXTRACTION_PROTOCOL.md",
    "docs/METHODS_AUTOMATED_CURATION.md", "docs/HARMONIZATION_REPORT.md", "docs/LIMITATIONS.md",
    "docs/RELEASE_READINESS.md", "docs/MANUSCRIPT_OUTLINE.md",
]
DIRS = ["paper/figures", "data/curated/extractions"]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="1.0")
    a = ap.parse_args()
    name = f"photodeg-bench-v{a.version}.0"
    out = ROOT / "release" / name
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    missing = []
    paths = [f.format(v=a.version) for f in FILES]
    for d in DIRS:
        paths += [str(p.relative_to(ROOT)) for p in sorted((ROOT / d).glob("*")) if p.is_file()]
    for rel in paths:
        src = ROOT / rel
        if not src.exists():
            missing.append(rel); continue
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    stats = json.loads((ROOT / "paper/stats.json").read_text())
    readiness = json.loads((ROOT / "release/READINESS.json").read_text()) if (ROOT / "release/READINESS.json").exists() else {}
    authors = json.loads((ROOT / "AUTHORS.json").read_text())
    meta = {
        "title": f"PhotoDeg-Bench v{a.version}.0: an open, harmonized benchmark of visible-light polymer deconstruction conditions and outcomes",
        "version": f"{a.version}.0", "built": dt.date.today().isoformat(),
        "creators": authors.get("authors", []), "license_data": "CC-BY-4.0", "license_code": "MIT",
        "curation": "AI-assisted autonomous curation (Claude) with deterministic source verification and independent blind re-extraction; see docs/METHODS_AUTOMATED_CURATION.md",
        "counts": {k: stats.get(k) for k in ("n_corpus_papers", "n_screened", "n_included_papers", "n_records_released",
                                             "n_molar_mass_records", "n_product_yield_records", "n_controls", "n_in_scope_no_fulltext")},
        "scientifically_ready": readiness.get("scientifically_ready"), "release_authorized": readiness.get("release_authorized"),
        "sources": ["Europe PMC REST API (open-access subset)", "OpenAlex API"],
        "missing_from_package": missing,
    }
    (out / "release_metadata.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    manifest = [{"path": str(p.relative_to(out)), "bytes": p.stat().st_size, "sha256": sha(p)} for p in sorted(out.rglob("*")) if p.is_file()]
    (out / "MANIFEST.json").write_text(json.dumps({"release": name, "files": manifest}, indent=1))
    z = ROOT / "release" / f"{name}.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(out.rglob("*")):
            if p.is_file():
                zf.write(p, f"{name}/{p.relative_to(out)}")
    print(f"{len(manifest)} files -> {out}; zip {z.name} ({z.stat().st_size} bytes, sha256 {sha(z)[:16]}...); missing: {missing}")


if __name__ == "__main__":
    main()
