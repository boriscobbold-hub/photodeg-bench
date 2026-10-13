#!/usr/bin/env python3
"""Build data/curated/records.csv and the evidence log from verified extraction files.

A record enters records.csv only if:
  - its paper's screening decision is 'include';
  - every field passed the deterministic source check (verify_records.py);
  - it was covered by an independent blind re-extraction (compare_blind.py);
  - no substantive disagreement for it is left unadjudicated (unresolved.py).
Records failing any test are written to data/curated/rejected_records.csv with the reason.

Also writes:
  data/curated/evidence.csv   one row per field: record_id, field, value, locator, source string, outcome
  data/curated/qa_flags.csv   one row per record flag, with the verifier concern or note behind it
"""
from __future__ import annotations

import csv
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(Path(__file__).parent))
_s = importlib.util.spec_from_file_location("ex", ROOT / "code" / "02_extract.py")
EX = importlib.util.module_from_spec(_s)
_s.loader.exec_module(EX)
import verify_records as VR  # noqa: E402
import unresolved as UR  # noqa: E402

V = ROOT / "data/curated/verification"
CURATOR = "Claude (AI) autonomous curation"

FLAG_RULES = [
    ("approximate_value", r"approx|almost|≈|∼|~\s?\d|estimat|around"),
    ("standard_conditions_applied", r"standard condition|optimi[sz]ed condition|general procedure|representative procedure|stated generally|same experimental procedure"),
    ("thermal_contribution", r"thermal|photothermal|heating|dark control .*(nearly|almost|comparable)|mostly thermal"),
    ("sec_estimate", r"estimation \(footnote|labelled an 'estimation'|'estimation'"),
    ("bimodal_sec", r"bimodal"),
]


def fmt(v):
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def main():
    deterministic = {}
    for line in open(V / "deterministic.jsonl", encoding="utf-8"):
        d = json.loads(line)
        deterministic.setdefault(d["record_id"], []).append(d)
    covered = set(json.loads((V / "blind_coverage.json").read_text()))
    unres = {(q["pmcid"], q["rid"]) for q in UR.unresolved()}
    concerns = {}
    for q in csv.DictReader(open(V / "adjudication_queue.csv", encoding="utf-8")):
        if q["type"] == "record_concern":
            concerns.setdefault((q["pmcid"], q["rid"]), []).append(q["detail"])

    cols = EX.RECORD_COLUMNS
    rows, rejected, evidence, flags = [], [], [], []
    for f in sorted((ROOT / "data/curated/extractions").glob("*.json")):
        d = json.loads(f.read_text())
        if d["screen"]["decision"] != "include":
            continue
        for r in d["records"]:
            key = f"{d['paper_key']}-{r['rid']}"
            rid = f"PDG-{d['pmcid']}-{r['rid']}"
            fields = {k: v for k, v in {**d.get("shared", {}), **r.get("fields", {})}.items() if v is not None}
            det = deterministic.get(key, [])
            det_ok = bool(det) and all(x["outcome"] in ("matched", "inferred") for x in det)
            blind_ok = key in covered
            reasons = []
            if not det_ok:
                reasons.append("deterministic source check failed")
            if not blind_ok:
                reasons.append("no independent blind re-extraction")
            if (d["pmcid"], r["rid"]) in unres:
                reasons.append("unresolved verification disagreement")
            row = {c: "" for c in cols}
            for k, ev in fields.items():
                if k in ("product_yields", "polymer_class") or k not in row:
                    continue
                row[k] = fmt(ev.get("v")) if isinstance(ev, dict) else fmt(ev)
            row["polymer_class"] = fmt(fields.get("polymer_class", {}).get("v"))
            ys = fields.get("product_yields") or []
            row["product_yields"] = "; ".join(f"{y['product']}: {fmt(y['v'])} {y.get('u', '%')}" for y in ys)
            row["yield_uncertainty"] = "; ".join(f"{y['product']}: {y['uncertainty']}" for y in ys if y.get("uncertainty"))
            if not row["products"] and ys:
                row["products"] = "; ".join(y["product"] for y in ys)
            note = r.get("notes", "")
            row.update({"record_id": rid, "paper_id": d["paper_id"], "doi": d["doi"], "pmcid": d["pmcid"],
                        "source_license": d["source_license"], "locator": r.get("primary_loc", ""),
                        "is_control": "y" if r.get("is_control") else "n",
                        "extraction_method": d.get("extraction_method", ""), "extractor": d.get("extractor", ""),
                        "notes": note, "curator": CURATOR, "curation_date": "2026-10-12",
                        "source_verified": "y" if det_ok else "n",
                        "blind_verified": "y" if blind_ok and (d["pmcid"], r["rid"]) not in unres else "n"})
            text = " ".join([note] + concerns.get((d["pmcid"], r["rid"]), []))
            fl = sorted({name for name, pat in FLAG_RULES if re.search(pat, text, re.I)})
            temp = fields.get("temperature_c", {}).get("v") if isinstance(fields.get("temperature_c"), dict) else None
            if isinstance(temp, (int, float)) and temp >= 80:
                fl = sorted(set(fl) | {"heated_ge_80C"})
            row["qa_flags"] = ";".join(fl)
            for name in fl:
                src = [c for c in [note] + concerns.get((d["pmcid"], r["rid"]), [])
                       if any(re.search(p, c, re.I) for n, p in FLAG_RULES if n == name)][:2]
                flags.append({"record_id": rid, "flag": name, "evidence": " | ".join(s[:200] for s in src) or f"temperature_c = {temp}"})
            for x in det:
                ev = fields.get(x["field"]) if not x["field"].startswith("product_yields") else None
                evidence.append({"record_id": rid, "field": x["field"], "value": fmt(x["value"]), "locator": x["loc"] or "",
                                 "source_string": x.get("s") or "",
                                 "inferred_reason": (ev.get("inferred") if isinstance(ev, dict) else "") or (x["detail"] if x["outcome"] == "inferred" else ""),
                                 "outcome": x["outcome"]})
            (rejected if reasons else rows).append({**row, **({"rejection_reason": "; ".join(reasons)} if reasons else {})})

    out = ROOT / "data/curated"
    with open(out / "records.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    with open(out / "rejected_records.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols + ["rejection_reason"], extrasaction="ignore"); w.writeheader(); w.writerows(rejected)
    with open(out / "evidence.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["record_id", "field", "value", "locator", "source_string", "inferred_reason", "outcome"])
        w.writeheader(); w.writerows(evidence)
    with open(out / "qa_flags.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["record_id", "flag", "evidence"]); w.writeheader(); w.writerows(flags)
    print(f"{len(rows)} records released to records.csv; {len(rejected)} rejected; {len(evidence)} evidence rows; {len(flags)} flags")


if __name__ == "__main__":
    main()
