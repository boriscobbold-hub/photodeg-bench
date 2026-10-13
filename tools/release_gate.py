#!/usr/bin/env python3
"""Release gate: scientific readiness (machine-checked) vs release authorization (the author's).

  python tools/release_gate.py --mode readiness   # run every machine check, write release/READINESS.json
                                                  # and docs/RELEASE_READINESS.md; exit 0 if scientifically ready
  python tools/release_gate.py --mode publish     # additionally require author metadata, endorsement of
                                                  # escalated rules, a signed release/AUTHORIZATION.json, and a
                                                  # clean placeholder/secret scan; exit 0 only if all pass

Scientific readiness (S*) can be reached autonomously. Release authorization (A*) cannot: it needs the
author's own name, ORCID and decision. The authorization is a written file (release/AUTHORIZATION.json),
not a cryptographic signature: anyone with write access could create it, so publishing credentials should
be held only by the author. Nothing here marks unresolved material as verified; a failed
check stays failed until its cause is fixed.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
VERSION = "1.0"
PLACEHOLDER = re.compile(r"\[(VERIFY|ASK|insert|DOI|TARGET)[^\]]*\]", re.I)


def sh(args, **kw):
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True, **kw)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read_csv(p):
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def check(cid, name, ok, detail, kind="science"):
    status = ("pass" if ok else "fail") if kind == "science" else ("pass" if ok else "pending_author")
    return {"id": cid, "check": name, "status": status, "detail": detail, "kind": kind}


def scientific_checks():
    out = []
    r = sh([PY, "-m", "unittest", "discover", "-s", "tests"])
    tail = (r.stderr or "").strip().splitlines()[-1:] or [""]
    out.append(check("S1", "test suite passes", r.returncode == 0, tail[0]))

    r = sh([PY, "code/03_validate.py"])
    out.append(check("S2", "schema and value validation: 0 errors", r.returncode == 0, r.stdout.strip()))

    r = sh([PY, "code/05_qa.py", "--version", VERSION])
    m = re.search(r"RESULT: (\w+).*", r.stdout)
    out.append(check("S3", "QA report passes (no critical failures)", r.returncode == 0, m.group(0) if m else r.stdout[-200:]))

    rel = ROOT / f"data/processed/photodeg_bench_v{VERSION}.csv"
    rows = read_csv(rel) if rel.exists() else []
    unverified = [x["record_id"] for x in rows if x.get("source_verified") != "y" or x.get("blind_verified") != "y"]
    out.append(check("S4", "every released record source-verified and independently re-extracted",
                     bool(rows) and not unverified, f"{len(rows)} records; unverified: {unverified[:5]}"))

    sys.path.insert(0, str(ROOT / "code/curation"))
    import unresolved as UR
    un = UR.unresolved()
    out.append(check("S5", "no unresolved verification disagreements", not un, f"{len(un)} unresolved"))

    import yaml
    rules = yaml.safe_load((ROOT / "rules/harmonization.yaml").read_text())["rules"]
    bad = [k for k, v in rules.items() if v.get("required") and (v.get("status") != "set" or not str(v.get("rationale", "")).strip())]
    out.append(check("S6", "every required harmonization rule set and justified", not bad, f"missing: {bad}" if bad else f"{len(rules)} rules"))

    figdir = ROOT / "paper/figures"
    with tempfile.TemporaryDirectory() as td:
        final = (ROOT / "release/.figures_final").exists()
        args = [PY, "code/06_figures.py", "--version", VERSION, "--out-dir", td] + (["--final"] if final else [])
        r = sh(args)
        diffs = []
        for p in sorted(Path(td).glob("*.png")):
            q = figdir / p.name
            if not q.exists() or sha(p) != sha(q):
                diffs.append(p.name)
    out.append(check("S7", "figures reproduce byte-for-byte from the final dataset", r.returncode == 0 and not diffs,
                     f"differing: {diffs}" if diffs else "all PNGs identical on regeneration"))

    prov = (ROOT / "data/raw/PROVENANCE.txt").read_text() if (ROOT / "data/raw/PROVENANCE.txt").exists() else ""
    missing = []
    for pm in sorted({x["pmcid"] for x in rows}):
        f = ROOT / "data/raw/fulltext" / f"{pm}.xml"
        if f.exists():
            if f"sha256:{sha(f)}" not in prov:
                missing.append(f"{pm} (hash not in PROVENANCE)")
        elif f"fulltext/{pm}.xml" not in prov:
            missing.append(f"{pm} (no provenance line)")
    out.append(check("S8", "every source article has a provenance record (and matching hash when present)", not missing, f"problems: {missing}" if missing else "ok"))

    allowed = {a.lower() for a in rules["R14_source_license_policy"].get("allowed", [])}
    badlic = sorted({x["source_license"] for x in rows if x["source_license"].lower().replace(" ", "-") not in allowed})
    lc = ROOT / "data/curated/license_check.csv"
    lic_rows = read_csv(lc) if lc.exists() else []
    disagree = [x["pmcid"] for x in lic_rows if x["agrees"] != "y"]
    unchecked = sorted({x["pmcid"] for x in rows} - {x["pmcid"] for x in lic_rows})
    ok9 = not badlic and not disagree and not unchecked
    out.append(check("S9", "source licenses allowed by R14 and confirmed against Crossref", ok9,
                     f"not allowed {badlic}; Crossref disagrees {disagree}; unchecked {unchecked}" if not ok9 else f"{len(lic_rows)} articles confirmed"))

    r = sh([PY, "tools/publish_gate.py", "."])
    secrets = [l for l in r.stdout.splitlines() if "secret" in l.lower() or "token" in l.lower() or "private key" in l.lower() or "credential" in l.lower()]
    out.append(check("S10", "no secrets or credentials in the repository", not secrets, "; ".join(secrets) or "none found"))

    stats = json.loads((ROOT / "paper/stats.json").read_text()) if (ROOT / "paper/stats.json").exists() else {}
    out.append(check("S11", "stats file agrees with the release table", stats.get("n_records_released") == len(rows),
                     f"stats {stats.get('n_records_released')} vs table {len(rows)}"))
    return out


def author_checks():
    out = []
    files = ["AUTHORS.json", "CITATION.cff", "LICENSE", "docs/zenodo_metadata.json"]
    pending = [f for f in files if PLACEHOLDER.search((ROOT / f).read_text())]
    out.append(check("A1", "author metadata complete (AUTHORS.json, CITATION.cff, LICENSE, Zenodo metadata)",
                     not pending, f"placeholders remain in: {pending}" if pending else "ok", kind="author"))
    import yaml
    rules = yaml.safe_load((ROOT / "rules/harmonization.yaml").read_text())["rules"]
    esc = [k for k, v in rules.items() if v.get("escalate") and not v.get("endorsed_by")]
    out.append(check("A2", "escalated scientific/legal rules endorsed by the author", not esc, f"awaiting: {esc}" if esc else "ok", kind="author"))
    auth = ROOT / "release/AUTHORIZATION.json"
    ok = False
    detail = "release/AUTHORIZATION.json not present"
    if auth.exists():
        d = json.loads(auth.read_text())
        ok = all(d.get(k) for k in ("authorized_by", "date", "statement", "version")) and d.get("version") == VERSION
        detail = "ok" if ok else "incomplete authorization file"
    out.append(check("A3", "public release authorized by the author (written authorization file; not a cryptographic signature)", ok, detail, kind="author"))
    return out


def write_reports(checks):
    sci_ok = all(c["status"] == "pass" for c in checks if c["kind"] == "science")
    auth_ok = all(c["status"] == "pass" for c in checks if c["kind"] == "author")
    rep = {"version": VERSION, "generated": dt.datetime.now().isoformat(timespec="seconds"),
           "scientifically_ready": sci_ok, "release_authorized": auth_ok, "checks": checks}
    (ROOT / "release").mkdir(exist_ok=True)
    (ROOT / "release/READINESS.json").write_text(json.dumps(rep, indent=1))
    L = [f"# Release readiness: PhotoDeg-Bench v{VERSION}", "",
         f"Generated {rep['generated']} by `tools/release_gate.py`. Regenerate; do not edit by hand.", "",
         f"**Scientific readiness: {'PASS' if sci_ok else 'FAIL'}.** **Release authorization: {'complete' if auth_ok else 'PENDING (author)'}.**", "",
         "| ID | Check | Status | Detail |", "|---|---|---|---|"]
    for c in checks:
        L.append(f"| {c['id']} | {c['check']} | {c['status']} | {str(c['detail']).replace('|', '/')[:160]} |")
    (ROOT / "docs/RELEASE_READINESS.md").write_text("\n".join(L) + "\n")
    return sci_ok, auth_ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["readiness", "publish"], default="readiness")
    a = ap.parse_args()
    checks = scientific_checks() + author_checks()
    sci_ok, auth_ok = write_reports(checks)
    for c in checks:
        print(f"{c['id']:4s} {c['status']:15s} {c['check']}  [{str(c['detail'])[:110]}]")
    print(f"\nscientifically ready: {sci_ok}   release authorized: {auth_ok}")
    if a.mode == "readiness":
        return 0 if sci_ok else 1
    if not (sci_ok and auth_ok):
        print("publish refused: scientific readiness and author authorization are both required")
        return 1
    r = sh([PY, "tools/publish_gate.py", "."])
    print(r.stdout)
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
