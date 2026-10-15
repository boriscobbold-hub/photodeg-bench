#!/usr/bin/env python3
"""Step 3: validate curated records before harmonization.

Reads   data/curated/records.csv, data/curated/screening.csv
Writes  data/processed/validation_report.txt
Exit    0 when there are no errors (warnings allowed), 1 otherwise.

Errors block harmonization (bad numbers, missing provenance, unreviewed records).
Warnings are things a curator should look at but may be correct (M_after > M_before,
wavelength outside 380-780 nm, unusual dispersity).

Usage
  python code/03_validate.py
  python code/03_validate.py --records tests/fixtures/synthetic_records.csv --screening tests/fixtures/synthetic_screening.csv
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import sys
from pathlib import Path

from common import CURATED, PROCESSED

MASS_UNITS = {"kg/mol", "g/mol", "kDa", "Da"}
TIME_UNITS = {"s", "min", "h", "d"}
CAL_CODES = {"conventional_PS", "conventional_PMMA", "conventional_PEG_PEO", "universal_calibration",
             "absolute_MALS", "triple_detection", "high_temperature_SEC", "MALDI_TOF", "DOSY_NMR",
             "other", "not_reported"}
MASS_FIELDS = ["mn_before", "mw_before", "mp_before", "mn_after", "mw_after", "mp_after"]
NUMERIC = MASS_FIELDS + ["disp_before", "disp_after", "sec_temperature_c", "catalyst_loading", "wavelength_nm",
                         "irradiance", "concentration", "temperature_c", "time"]
REQUIRED = ["record_id", "paper_id", "doi", "source_license", "locator", "polymer",
            "curator", "curation_date", "source_verified", "blind_verified"]
YIELDS_RE = re.compile(r"^\s*[^:;]+:\s*\d+(\.\d+)?\s*(%|mol%|wt%|mg|g|µmol|umol|mmol)\s*$")


def num(v):
    v = (v or "").strip()
    if v == "":
        return None
    return float(v)


def validate(records, screening):
    errors, warnings = [], []
    included = {p["paper_id"] for p in screening if p.get("include", "").strip().lower() in ("y", "yes", "1", "true")}
    seen = set()
    for i, r in enumerate(records, start=2):  # row 1 is the header
        rid = r.get("record_id", "").strip() or f"(row {i})"
        tag = f"{rid}"
        if rid in seen:
            errors.append(f"{tag}: duplicate record_id")
        seen.add(rid)
        for f in REQUIRED:
            if not (r.get(f) or "").strip():
                errors.append(f"{tag}: missing {f}")
        if r.get("paper_id") and included and r["paper_id"] not in included:
            errors.append(f"{tag}: paper_id {r['paper_id']} is not marked include=y in screening.csv")
        if (r.get("source_verified") or "").strip().lower() != "y":
            errors.append(f"{tag}: source_verified is not 'y' (every value must match its source string at its locator)")
        if (r.get("blind_verified") or "").strip().lower() != "y":
            errors.append(f"{tag}: blind_verified is not 'y' (independent re-extraction with no unresolved disagreement)")
        has_mass = any((r.get(f"{k}_{s_}") or "").strip() for k in ("mn", "mw", "mp") for s_ in ("before", "after"))
        if not has_mass and not (r.get("product_yields") or "").strip():
            errors.append(f"{tag}: no benchmark endpoint (molar mass or product yield)")
        d = (r.get("curation_date") or "").strip()
        if d:
            try:
                dt.date.fromisoformat(d)
            except ValueError:
                errors.append(f"{tag}: curation_date '{d}' is not YYYY-MM-DD")
        vals = {}
        for f in NUMERIC:
            try:
                vals[f] = num(r.get(f))
            except ValueError:
                errors.append(f"{tag}: {f}='{r.get(f)}' is not a number")
                vals[f] = None
        for f in MASS_FIELDS:
            if vals.get(f) is not None and vals[f] <= 0:
                errors.append(f"{tag}: {f} must be > 0")
        for side in ("before", "after"):
            has = any(vals.get(f"{k}_{side}") is not None for k in ("mn", "mw", "mp"))
            unit = (r.get(f"mass_unit_{side}") or "").strip()
            if has and unit not in MASS_UNITS:
                errors.append(f"{tag}: mass_unit_{side} '{unit}' must be one of {sorted(MASS_UNITS)}")
            disp = vals.get(f"disp_{side}")
            if disp is not None and disp < 1.0:
                errors.append(f"{tag}: disp_{side}={disp} < 1")
            elif disp is not None and disp > 10:
                warnings.append(f"{tag}: disp_{side}={disp} is unusually high")
            mn, mw = vals.get(f"mn_{side}"), vals.get(f"mw_{side}")
            if mn and mw:
                if mw < mn:
                    errors.append(f"{tag}: mw_{side} < mn_{side}")
                if disp is not None and abs(mw / mn - disp) > 0.15 * disp:
                    warnings.append(f"{tag}: disp_{side}={disp} disagrees with Mw/Mn={mw / mn:.2f} by >15%")
        pass
        for k in ("mn", "mw", "mp"):
            b, a = vals.get(f"{k}_before"), vals.get(f"{k}_after")
            ub, ua = (r.get("mass_unit_before") or "").strip(), (r.get("mass_unit_after") or "").strip()
            if b and a and ub == ua and a > b:
                warnings.append(f"{tag}: {k}_after > {k}_before (crosslinking, fractionation, or a transcription slip?)")
        cal = (r.get("sec_calibration") or "").strip()
        if has_mass and not cal:
            errors.append(f"{tag}: molar-mass record without sec_calibration (use not_reported if the paper gives none)")
        if cal and cal not in CAL_CODES:
            errors.append(f"{tag}: sec_calibration '{cal}' not in {sorted(CAL_CODES)}")
        wl = vals.get("wavelength_nm")
        if wl is not None and not 300 <= wl <= 900:
            errors.append(f"{tag}: wavelength_nm={wl} outside 300-900")
        elif wl is not None and not 380 <= wl <= 780:
            warnings.append(f"{tag}: wavelength_nm={wl} outside 380-780 nm (check R08)")
        wr = (r.get("wavelength_range_nm") or "").strip()
        if wr and not re.fullmatch(r"\d{3}-\d{3}", wr):
            errors.append(f"{tag}: wavelength_range_nm '{wr}' must look like 400-700")
        if wl is None and not wr and not (r.get("light_color") or "").strip() and not (r.get("light_source") or "").strip():
            warnings.append(f"{tag}: no light description at all")
        if vals.get("time") is not None:
            if vals["time"] <= 0:
                errors.append(f"{tag}: time must be > 0")
            if (r.get("time_unit") or "").strip() not in TIME_UNITS:  # noqa
                errors.append(f"{tag}: time_unit '{r.get('time_unit')}' must be one of {sorted(TIME_UNITS)}")
        py = (r.get("product_yields") or "").strip()
        if py:
            for part in py.split(";"):
                if part.strip() and not YIELDS_RE.match(part):
                    errors.append(f"{tag}: product_yields item '{part.strip()}' must look like 'benzoic acid: 40 %'")
        if r.get("doi") and not re.match(r"^10\.\d{4,9}/\S+$", r["doi"].strip()):
            errors.append(f"{tag}: doi '{r['doi']}' is not a bare DOI (10.xxxx/...)")
    return errors, warnings


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--records", default=str(CURATED / "records.csv"))
    ap.add_argument("--screening", default=str(CURATED / "screening.csv"))
    ap.add_argument("--report", default=str(PROCESSED / "validation_report.txt"))
    a = ap.parse_args()
    with open(a.records, encoding="utf-8") as f:
        records = list(csv.DictReader(f))
    screening = []
    if Path(a.screening).exists():
        with open(a.screening, encoding="utf-8") as f:
            screening = list(csv.DictReader(f))
    errors, warnings = validate(records, screening)
    if not records:
        warnings.append("records.csv has no records yet")
    Path(a.report).parent.mkdir(parents=True, exist_ok=True)
    with open(a.report, "w", encoding="utf-8") as f:
        f.write(f"PhotoDeg-Bench validation report  {dt.date.today().isoformat()}\n")
        f.write(f"records: {len(records)}   errors: {len(errors)}   warnings: {len(warnings)}\n\n")
        f.write("ERRORS\n" + "".join(f"  {e}\n" for e in errors) + "\nWARNINGS\n" + "".join(f"  {w}\n" for w in warnings))
    print(f"{len(records)} records, {len(errors)} errors, {len(warnings)} warnings -> {a.report}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
