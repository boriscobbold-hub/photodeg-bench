#!/usr/bin/env python3
"""Step 2b: rank screened papers by how much benchmark-relevant evidence their full text holds.

A screening aid only. It never sets include/exclude; the curator does that in screening.csv.

Reads   data/curated/screening.csv, data/processed/candidates.jsonl
Writes  data/processed/triage.csv   (one row per screened paper, highest score first)

topic = on_topic when the paper's own title+abstract mention light, a deconstruction outcome
and a synthetic polymer; otherwise it names what is missing. Sorted: on-topic first, then score.

Score (0-6), one point each:
  sec_mass      at least one Mn/Mw/Mp candidate with a mass unit
  mass_table    a table with a recognised Mn/Mw/Mp column
  sec_method    an SEC calibration mention
  visible_light a wavelength in 380-780 nm or a visible colour (not white)
  polymer       a named polymer
  catalyst      a named catalyst
"""
import collections
import csv
import importlib.util
import json
import re
from pathlib import Path

from common import CURATED, PROCESSED, ROOT

_spec = importlib.util.spec_from_file_location("x", Path(__file__).parent / "02_extract.py")
_x = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_x)

LIGHT = re.compile(r"visible|light|photo|\bLEDs?\b|solar|sunlight|irradiat", re.I)
DECON = re.compile(r"depolymeri|degrad|deconstruct|upcycl|scission|recycl|valori[sz]", re.I)
SYNTH = re.compile(r"polystyrene|polyethylene|polypropylene|poly\(methyl methacrylate\)|\bPMMA\b|polyacrylate|poly\(\w*\s?acrylate\)|"
                   r"polymethacrylate|poly\(vinyl|polyvinyl|\bPVC\b|\bPET\b|polyester|polylactide|poly\(lactic|\bPLA\b|polycarbonate|"
                   r"polyurethane|polyamide|nylon|plastics?\b|\bHDPE\b|\bLDPE\b|polyolefin|polyketone|polyether|vinyl polymer|"
                   r"synthetic polymer|commodity polymer|polymer chains?|macromolecul", re.I)


def topic(path):
    """'on_topic' when title+abstract mention light, a deconstruction outcome and a synthetic polymer."""
    text = []
    try:
        for loc, kind, payload in _x.parse_jats(path):
            if loc in ("title", "abstract"):
                text.append(payload)
            elif loc not in ("title", "abstract"):
                break
    except Exception:  # malformed XML: leave for the curator
        return "unparsed"
    t = " ".join(text)
    hits = [n for n, rx in (("light", LIGHT), ("deconstruction", DECON), ("synthetic_polymer", SYNTH)) if rx.search(t)]
    return "on_topic" if len(hits) == 3 else "missing:" + ",".join(n for n in ("light", "deconstruction", "synthetic_polymer") if n not in hits)

papers = list(csv.DictReader(open(CURATED / "screening.csv", encoding="utf-8")))
sig = collections.defaultdict(set)
polys = collections.defaultdict(collections.Counter)
with open(PROCESSED / "candidates.jsonl", encoding="utf-8") as f:
    for line in f:
        c = json.loads(line)
        p, fld = c["paper_id"], c["field"]
        if fld in ("Mn", "Mw", "Mp") and c.get("unit"):
            sig[p].add("sec_mass")
        if fld == "table_columns_recognised" and any(k in c["value"] for k in ("=Mn", "=Mw", "=Mp")):
            sig[p].add("mass_table")
        if fld == "sec_calibration":
            sig[p].add("sec_method")
        if (fld == "wavelength_nm" and 380 <= float(c["value"]) <= 780) or (fld == "light_color" and c["value"] != "white"):
            sig[p].add("visible_light")
        if fld == "polymer":
            sig[p].add("polymer")
            polys[p][c["value"]] += 1
        if fld == "catalyst":
            sig[p].add("catalyst")
ORDER = ["sec_mass", "mass_table", "sec_method", "visible_light", "polymer", "catalyst"]
rows = []
for p in papers:
    s = sig.get(p["paper_id"], set())
    has_ft = bool(p.get("fulltext")) and not p["fulltext"].startswith("unavailable")
    rows.append({"paper_id": p["paper_id"], "doi": p["doi"], "year": p["year"], "license": p["license"],
                 "has_fulltext": "y" if has_ft else "n",
                 "topic": topic(ROOT / p["fulltext"]) if has_ft else "",
                 "score": len(s) if has_ft else "",
                 "signals": ";".join(k for k in ORDER if k in s),
                 "top_polymers": "; ".join(k for k, _ in polys[p["paper_id"]].most_common(3)),
                 "title": p["title"]})
rows.sort(key=lambda r: (r["has_fulltext"] != "y", r["topic"] != "on_topic", -(r["score"] or 0), r["paper_id"]))
with open(PROCESSED / "triage.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
on = [r for r in rows if r["topic"] == "on_topic"]
print(f"full-text papers on topic: {len(on)} of {sum(r['has_fulltext'] == 'y' for r in rows)}")
print("score distribution (on-topic):", dict(sorted(collections.Counter(r["score"] for r in on).items(), reverse=True)))
print(f"{len(rows)} papers ranked -> data/processed/triage.csv")
