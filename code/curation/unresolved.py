#!/usr/bin/env python3
"""List substantive verification disagreements that have no logged adjudication.

Substantive = a disagreement or blind_null on a key field (numbers, polymer, catalyst, solvent,
atmosphere, time, temperature, wavelength, products, yields), after treating text fields that share
>= 50 % of their tokens as agreeing (paraphrase). Resolved = a row in adjudications.csv matching
pmcid, record and field (or field '*'). Used by build_records.py as a release gate.
"""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V = ROOT / "data/curated/verification"
KEY = {"mn_before", "mn_after", "mw_before", "mw_after", "mp_before", "mp_after", "disp_before", "disp_after", "time",
       "temperature_c", "wavelength_nm", "catalyst", "catalyst_loading", "solvent", "atmosphere", "polymer", "concentration",
       "sec_calibration", "products"}
TEXT = {"catalyst", "solvent", "atmosphere", "polymer", "products", "sec_calibration"}


def tokens(x):
    return set(re.findall(r"[a-z0-9.]+", str(x).lower()))


def unresolved():
    adj = list(csv.DictReader(open(V / "adjudications.csv", encoding="utf-8")))
    def adjudicated(pm, rid, field):
        for a in adj:
            if a["pmcid"] != pm:
                continue
            rids = a["rids"].split(";")
            if (a["rids"] == "*" or rid in rids) and (a["field"] == field or a["field"] == "*"):
                return True
        return False
    out = []
    for q in csv.DictReader(open(V / "adjudication_queue.csv", encoding="utf-8")):
        f = q["field"]
        if q["type"] not in ("disagree", "blind_null"):
            continue
        if not (f in KEY or f.startswith("yield:")):
            continue
        if q["type"] == "disagree" and f in TEXT:
            a, b = tokens(q["extracted"]), tokens(q["blind"])
            if a and b and len(a & b) / min(len(a), len(b)) >= 0.5:
                continue
        if adjudicated(q["pmcid"], q["rid"], f):
            continue
        out.append(q)
    return out


if __name__ == "__main__":
    for q in unresolved():
        print(q["pmcid"], q["rid"], q["field"], q["type"], "| ext:", q["extracted"][:60], "| blind:", q["blind"][:60])
