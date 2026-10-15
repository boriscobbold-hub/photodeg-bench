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
import hashlib
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

# Flags are computed from structured evidence where possible (audit finding 6):
#   approximate_value       a recorded number's own source string says ~, ≈, approx., almost, around, estimation
#   conditions_from_other_block  a condition field (time, solvent, temperature, atmosphere, light, loading,
#                           concentration) was read from a different text block/table than the record's result
#   heated_ge_80C           temperature_c >= 80
#   thermal_contribution    a dark control in the same paper (same polymer, temperature, catalyst, loading) gives at least half
#                           of a lit record's product yield, or a verifier/curator note says the run is mostly thermal
#   sec_estimate / bimodal_sec  the paper labels the molar mass an estimate / the distribution bimodal
APPROX = re.compile(r"~|≈|∼|approx|almost|around|estimat|nearly", re.I)
COND_FIELDS = ("time", "solvent", "temperature_c", "atmosphere", "wavelength_nm", "light_source", "catalyst_loading", "concentration")
FLAG_RULES = [
    ("sec_estimate", r"\bestimation\b|labelled an 'estimation'"),
    ("bimodal_sec", r"bimodal"),
    ("thermal_contribution", r"mostly thermal|thermal reaction nearly|thermal alone gives|dark control gives most"),
]


def is_borrowed(cond_loc, primary_block):
    """A condition is 'borrowed' when it was read from another Results/Discussion paragraph or another
    table/figure than the record's own result. Methods/Experimental procedures and the result's own
    table, caption or footnote are where conditions normally live, so they do not count."""
    cb = block_of(cond_loc)
    if cb == primary_block:
        return False
    if re.match(r"(?i)(\d+\.?\s*)?(methods?|experimental|materials)", cb) or re.search(r"(?i)> *(general procedure|experimental|methods?)", cb):
        return False
    pb_label = re.match(r"(?i)((?:table|fig\.?|figure)\s*[\w.]*)", primary_block or "")
    if pb_label and cb.lower().startswith(pb_label.group(1).lower().rstrip(".")):
        return False
    return True


def block_of(loc):
    loc = re.sub(r"\s+", " ", loc or "")
    m = re.match(r"(.*?)( r\d+( c\d+)?| h c\d+| footnote)$", loc)
    return (m.group(1) if m else loc).strip()


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
            for val, unit in (("time", "time_unit"), ("catalyst_loading", "catalyst_loading_unit"), ("irradiance", "irradiance_unit"), ("concentration", "concentration_unit")):
                if not row.get(val):
                    row[unit] = ""
            if not any(row.get(f"{k}_before") for k in ("mn", "mw", "mp")):
                row["mass_unit_before"] = ""
            if not any(row.get(f"{k}_after") for k in ("mn", "mw", "mp")):
                row["mass_unit_after"] = ""
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
            fl = {name for name, pat in FLAG_RULES if re.search(pat, text, re.I)}
            num_fields = [k for k in ("mn_before", "mn_after", "mw_before", "mw_after", "mp_before", "mp_after", "time", "temperature_c")
                          if isinstance(fields.get(k), dict) and fields[k].get("s")]
            if any(APPROX.search(fields[k]["s"]) for k in num_fields) or any(APPROX.search(y.get("s", "")) for y in ys):
                fl.add("approximate_value")
            pb = block_of(r.get("primary_loc", ""))
            borrowed = [k for k in COND_FIELDS if isinstance(fields.get(k), dict) and fields[k].get("loc")
                        and is_borrowed(fields[k]["loc"], pb)]
            if borrowed:
                fl.add("conditions_from_other_block")
            fl = sorted(fl)
            temp = fields.get("temperature_c", {}).get("v") if isinstance(fields.get("temperature_c"), dict) else None
            if isinstance(temp, (int, float)) and temp >= 80:
                fl = sorted(set(fl) | {"heated_ge_80C"})
            row["qa_flags"] = ";".join(fl)
            for name in fl:
                if name == "approximate_value":
                    ev_txt = "; ".join(f"{k}: {fields[k]['s']}" for k in num_fields if APPROX.search(fields[k]["s"])) or \
                             "; ".join(y["s"] for y in ys if APPROX.search(y.get("s", "")))
                elif name == "conditions_from_other_block":
                    ev_txt = "; ".join(f"{k} from '{fields[k]['loc']}'" for k in borrowed) + f" (result at '{r.get('primary_loc', '')}')"
                elif name == "heated_ge_80C":
                    ev_txt = f"temperature_c = {temp}"
                else:
                    ev_txt = " | ".join(c[:200] for c in [note] + concerns.get((d["pmcid"], r["rid"]), [])
                                        if any(re.search(p, c, re.I) for n, p in FLAG_RULES if n == name))[:400]
                flags.append({"record_id": rid, "flag": name, "evidence": ev_txt})
            open_lic = d["source_license"].lower().replace(" ", "-") in ("cc-by", "cc0", "cc-by-sa")
            for x in det:
                ev = fields.get(x["field"]) if not x["field"].startswith("product_yields") else None
                evidence.append({"record_id": rid, "field": x["field"], "value": fmt(x["value"]), "locator": x["loc"] or "",
                                 "source_string": (x.get("s") or "") if open_lic else "",
                                 "source_string_sha256": hashlib.sha256((x.get("s") or "").encode()).hexdigest() if x.get("s") else "",
                                 "source_license": d["source_license"],
                                 "inferred_reason": (ev.get("inferred") if isinstance(ev, dict) else "") or (x["detail"] if x["outcome"] == "inferred" else ""),
                                 "outcome": x["outcome"]})
            (rejected if reasons else rows).append({**row, **({"rejection_reason": "; ".join(reasons)} if reasons else {})})

    # Structured thermal_contribution: a dark control in the same paper with the same polymer, temperature, catalyst and loading that
    # gives >= 50 % of a lit record's yield of the same product.
    def yields_of(row):
        out = {}
        for part in (row.get("product_yields") or "").split(";"):
            if ":" in part and "%" in part:
                name, val = part.split(":", 1)
                try:
                    out[name.strip()] = float(val.replace("%", "").strip())
                except ValueError:
                    pass
        return out
    dark = [x for x in rows if x["is_control"] == "y" and x.get("light_source", "").lower().startswith("none")]
    for x in rows:
        if x["is_control"] == "y":
            continue
        for dc in dark:
            if dc["pmcid"] != x["pmcid"] or any(dc.get(k) != x.get(k) for k in ("catalyst", "catalyst_loading", "polymer")) \
                    or (dc.get("temperature_c") and dc.get("temperature_c") != x.get("temperature_c")):
                continue
            lit, dk = yields_of(x), yields_of(dc)
            hits = [p for p in lit if p in dk and lit[p] > 0 and dk[p] >= 0.5 * lit[p]]
            def red(row):
                for k in ("mn", "mw"):
                    try:
                        b, a_ = float(row.get(f"{k}_before") or "x"), float(row.get(f"{k}_after") or "x")
                        return k, 1 - a_ / b
                    except ValueError:
                        continue
                return None, None
            kx, rx = red(x)
            kd, rd = red(dc)
            if kx and kx == kd and rx > 0 and rd >= 0.5 * rx:
                hits.append(f"{kx} reduction {rd:.0%} dark vs {rx:.0%} lit")
                dk[hits[-1]] = rd * 100
                lit[hits[-1]] = rx * 100
            if hits:
                fl = set(filter(None, x["qa_flags"].split(";"))) | {"thermal_contribution"}
                x["qa_flags"] = ";".join(sorted(fl))
                flags.append({"record_id": x["record_id"], "flag": "thermal_contribution",
                              "evidence": f"dark control {dc['record_id']} ({dc.get('temperature_c') or 'temperature not stated'} °C): "
                                          + "; ".join(p if "reduction" in p else f"{p} {dk[p]:g}% dark vs {lit[p]:g}% lit" for p in hits)})

    out = ROOT / "data/curated"
    with open(out / "records.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    with open(out / "rejected_records.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols + ["rejection_reason"], extrasaction="ignore"); w.writeheader(); w.writerows(rejected)
    with open(out / "evidence.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["record_id", "field", "value", "locator", "source_string", "source_string_sha256", "source_license", "inferred_reason", "outcome"])
        w.writeheader(); w.writerows(evidence)
    with open(out / "qa_flags.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["record_id", "flag", "evidence"]); w.writeheader(); w.writerows(flags)
    print(f"{len(rows)} records released to records.csv; {len(rejected)} rejected; {len(evidence)} evidence rows; {len(flags)} flags")


if __name__ == "__main__":
    main()
