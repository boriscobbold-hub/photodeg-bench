#!/usr/bin/env python3
"""Agent D, deterministic half: check every extracted value against the source XML.

Each extraction file (data/curated/extractions/*.json) gives, for every field of every record,
the value, the locator where it was read, and the literal source string ('s') at that locator.
This script re-parses the article with the same parser the extractor used and checks:

  L  the locator exists in the article
  S  the source string occurs in the text of that block (after Unicode/whitespace normalisation)
  N  for numeric fields, the number parsed from the source string equals the recorded value
     (thousands separators, thin spaces, '~', '±' tails and decimal commas handled explicitly)

Field outcomes: matched | inferred (no locator; reason given, allowed only for INFERABLE fields)
                | mismatch | locator_missing | string_missing.
A record is 'verified' only if every field is matched or legitimately inferred.

Writes data/curated/verification/deterministic.jsonl (one line per field) and prints a summary.

Usage: python code/curation/verify_records.py [--paper <paper-file-stem>]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import unicodedata
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXTRACTIONS = ROOT / "data" / "curated" / "extractions"
OUT = ROOT / "data" / "curated" / "verification"

sys.path.insert(0, str(ROOT / "code"))
_s = importlib.util.spec_from_file_location("x", ROOT / "code" / "02_extract.py")
X = importlib.util.module_from_spec(_s)
_s.loader.exec_module(X)

NUMERIC = {"mn_before", "mw_before", "mp_before", "disp_before", "mn_after", "mw_after", "mp_after", "disp_after",
           "sec_temperature_c", "catalyst_loading", "wavelength_nm", "irradiance", "concentration", "temperature_c",
           "time", "replicates"}
# Fields that may be filled without a locator, because they are a classification of located facts
# or a unit convention; the reason must be given and is published.
INFERABLE = {"polymer_class", "mass_unit_before", "mass_unit_after", "light_color", "sec_calibration",
             "yield_basis", "time_unit", "catalyst_loading_unit", "irradiance_unit", "concentration_unit"}


def norm(t: str) -> str:
    t = unicodedata.normalize("NFKC", t)
    t = re.sub(r"[−–—‐‑]", "-", t)
    t = t.replace(" ", " ").replace(" ", " ").replace(" ", " ")
    return re.sub(r"\s+", " ", t).strip()


def squash(t: str) -> str:
    return re.sub(r"\s+", "", norm(t))


@lru_cache(maxsize=64)
def blocks(pmcid: str) -> dict:
    path = ROOT / "data" / "raw" / "fulltext" / f"{pmcid}.xml"
    out = {}
    for loc, kind, payload in X.parse_jats(path):
        if kind == "text":
            out.setdefault(norm(loc), []).append(payload)
        else:
            header, rows = payload
            base = norm(loc)
            out.setdefault(base, []).append(" | ".join(header) + "\n" + "\n".join(" | ".join(r) for r in rows))
            for j, h in enumerate(header):
                out.setdefault(f"{base} h c{j + 1}", []).append(h)
            for i, r in enumerate(rows):
                out.setdefault(f"{base} r{i + 1}", []).append(" | ".join(r))
                for j, c in enumerate(r):
                    out.setdefault(f"{base} r{i + 1} c{j + 1}", []).append(c)
    return {k: " ".join(v) for k, v in out.items()}


def numbers_in(s: str) -> list[float]:
    """All plausible readings of the numbers in s (first number considered primary)."""
    s = norm(s).replace("~", " ").replace("≈", " ")
    s = re.sub(r"(?<=\d)[ ](?=\d{3}\b)", "", s)          # '260 000' -> '260000'
    out = []
    words = {"duplicate": 2, "triplicate": 3, "quadruplicate": 4, "two": 2, "three": 3, "four": 4, "five": 5}
    for w, n in words.items():
        if re.search(rf"\b{w}\b", s, re.I):
            out.append(float(n))
    for m in re.finditer(r"\d+(?:[.,]\d+)*(?:[eE][-+]?\d+)?", s):
        tok = m.group(0)
        cands = set()
        if re.fullmatch(r"0,\d+", tok):                  # '0,065' is a decimal comma, never thousands
            cands.add(float(tok.replace(",", ".")))
        elif re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?", tok):
            cands.add(float(tok.replace(",", "")))
        if re.fullmatch(r"\d+,\d{1,2}", tok):            # decimal comma, e.g. '1,4'
            cands.add(float(tok.replace(",", ".")))
        try:
            cands.add(float(tok))
        except ValueError:
            pass
        out.extend(cands)
    return out


def check_field(pmcid, field, ev):
    if not isinstance(ev, dict):
        return "malformed", "field evidence must be an object"
    if not ev.get("loc"):
        if ev.get("inferred") and field in INFERABLE:
            return "inferred", ev["inferred"]
        return "mismatch", "no locator and field is not inferable"
    B = blocks(pmcid)
    loc = norm(ev["loc"])
    if loc not in B:
        return "locator_missing", f"locator '{ev['loc']}' not in article"
    text = B[loc]
    s = ev.get("s", "")
    if not s:
        return "mismatch", "no source string"
    if norm(s) not in norm(text) and squash(s) not in squash(text):
        return "string_missing", f"'{s}' not found at {ev['loc']}"
    if field in NUMERIC:
        try:
            v = float(ev["v"])
        except (TypeError, ValueError):
            return "mismatch", f"value {ev.get('v')!r} not numeric"
        scale = float(ev.get("scale", 1))   # e.g. header says 'Mn (kg/mol)' but value recorded in kg/mol -> 1
        if not any(abs(n * scale - v) <= 1e-9 * max(1, abs(v)) for n in numbers_in(s)):
            return "mismatch", f"value {v} not readable from '{s}'"
    return "matched", ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    files = sorted(EXTRACTIONS.glob("*.json"))
    if a.paper:
        files = [f for f in files if f.stem == a.paper]
    lines, summary = [], {"records": 0, "verified": 0, "fields": 0, "by_outcome": {}}
    for f in files:
        d = json.loads(f.read_text())
        if d.get("screen", {}).get("decision") != "include":
            continue
        shared = d.get("shared", {})
        for rec in d.get("records", []):
            rid = f"{d['paper_key']}-{rec['rid']}"
            fields = {**shared, **rec.get("fields", {})}
            ok = True
            items = []
            for field, ev in fields.items():
                if ev is None:          # explicit null: record overrides a shared field with 'not applicable'
                    continue
                if field == "product_yields":
                    for k, y in enumerate(ev):
                        items.append((f"product_yields[{k}]:{y.get('product')}", "yield_value", y))
                        items.append((f"product_yields[{k}].product", "product_name",
                                      {"v": y.get("product"), "loc": y.get("name_loc", y.get("loc")), "s": y.get("name_s", y.get("product"))}))
                else:
                    items.append((field, field, ev))
            for label, kind, ev in items:
                outcome, why = check_field(d["pmcid"], "replicates" if kind == "yield_value" else kind, ev)
                lines.append({"record_id": rid, "field": label, "value": ev.get("v") if isinstance(ev, dict) else ev,
                              "loc": ev.get("loc") if isinstance(ev, dict) else None, "s": ev.get("s") if isinstance(ev, dict) else None,
                              "outcome": outcome, "detail": why})
                summary["by_outcome"][outcome] = summary["by_outcome"].get(outcome, 0) + 1
                summary["fields"] += 1
                ok &= outcome in ("matched", "inferred")
            summary["records"] += 1
            summary["verified"] += ok
    with open(OUT / "deterministic.jsonl", "w", encoding="utf-8") as fo:
        for ln in lines:
            fo.write(json.dumps(ln, ensure_ascii=False) + "\n")
    print(json.dumps(summary, indent=1))
    bad = [l for l in lines if l["outcome"] not in ("matched", "inferred")]
    for l in bad[:60]:
        print(f"  {l['record_id']:28s} {l['field']:22s} {l['outcome']:16s} {l['detail']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
