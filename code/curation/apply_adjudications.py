#!/usr/bin/env python3
"""Apply adjudicated corrections to extraction files and log every decision.

Each adjudication was decided by reading the source passage (Claude, 2026-10-12) after the blind
comparison flagged it. Corrections are applied idempotently; the log is
data/curated/verification/adjudications.csv.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EX = ROOT / "data/curated/extractions"
LOG = ROOT / "data/curated/verification/adjudications.csv"

ADJ = []  # (pmcid, rids or '*', field, new_value_or_None, decision, rationale)


def A(pm, rids, field, new, decision, why):
    ADJ.append((pm, rids, field, new, decision, why))


# PMC9586668: the blind pass located an explicit statement of the atmosphere.
A("PMC9586668", "*", "atmosphere", {"v": "N2", "loc": "2 Experimental > 2.1 Materials ¶1",
  "s": "All reactions were performed under an inert atmosphere of nitrogen"}, "blind correct",
  "Materials section states reactions under N2; more specific than 'degassed'.")
A("PMC9586668", "*", "concentration_note", None, "keep extracted",
  "Blind noted 0.065 M is inconsistent with catalyst ratio; value kept as printed, basis (likely repeat units) unstated; noted.")

# PMC13590609: '1 g PP' is an amount, not a concentration; dark control time not stated in main text.
A("PMC13590609", ["a", "b", "c"], "concentration", None, "both partly",
  "'PP (1 g) and Cl-solvent (12 mL)' is an amount; concentration not stated as such. Removed; amount kept in notes.")
A("PMC13590609", ["a", "b", "c"], "concentration_unit", None, "follow-on", "concentration removed")
A("PMC13590609", ["c"], "time", None, "blind correct",
  "Dark control is Supplementary Table S3 entry 7; the 18 h comes from the representative procedure for lit runs.")
A("PMC13590609", ["d", "e"], "yield_alignment", None, "extraction correct",
  "Blind task d/e alignment differed (both anchored to the same paragraph). Source: d = PP/PET 1:1, ~70% TPA; e = pre-formed OPP5, 48.1%. 'Over 90%' (entries 1-2) is a bound and not recorded.")

# PMC12056016: PMMA results paragraph attaches no light, solvent, atmosphere or time; loading printed as ppm.
for f in ("wavelength_nm", "solvent", "atmosphere", "light_source", "irradiance", "irradiance_unit", "light_color", "concentration", "concentration_unit"):
    A("PMC12056016", ["d", "e"], f, None, "blind correct",
      "PMMA paragraph (Applications ¶2) gives none of these; values had been carried over from the PS general procedure.")
A("PMC12056016", ["d", "e"], "catalyst_loading", {"v": 500, "loc": "Results > Applications to diverse polymer types ¶2", "s": "only 500 ppm PTH-3CN"},
  "blind correct", "Loading printed as 500 ppm for PMMA.")
A("PMC12056016", ["d", "e"], "catalyst_loading_unit", {"v": "ppm", "inferred": "unit printed with the value"}, "blind correct", "as printed")
A("PMC12056016", ["a"], "concentration", None, "blind correct", "'1.0 mmol styrene unit' is an amount, not a concentration.")
A("PMC12056016", ["a"], "concentration_unit", None, "follow-on", "concentration removed")

# PMC12302232: gram-scale flow run does not restate the solvent.
A("PMC12302232", ["i"], "solvent", None, "blind correct", "Flow run (Results ¶9) does not state the solvent; standard batch solvent not assumed.")

# PMC11796324: footnote [d] marks NMR yields for entries 1, 2, 4; 'Inert' gas unnamed.
for rid in ("a", "b", "d"):
    A("PMC11796324", [rid], "yield_basis", {"v": "1H NMR (per mmol styrene repeat units)", "loc": "Table 1 footnote", "s": "[d] Yield determined by 1H NMR"},
      "blind correct", "Row carries footnote [d]: yields by 1H NMR, not GC-FID.")
for rid in ("c", "e", "f", "g", "h", "i", "j", "k", "l", "m"):
    A("PMC11796324", [rid], "yield_basis", {"v": "GC-FID (per mmol styrene repeat units)", "loc": "Table 1 footnote", "s": "Yields determined by GC-FID"},
      "both partly", "GC-FID per footnote [a]; basis is PS 'in monomer' units per the same footnote.")
A("PMC11796324", ["f"], "atmosphere", {"v": "inert (gas not named)", "loc": "Table 1 r6 c4", "s": "Inert, 24 h"}, "blind correct",
  "Printed 'Inert'; the gas is not named, so not coded as N2/Ar or 'degassed'.")

# Round 2 (after re-comparison)
A("PMC13590609", ["c"], "atmosphere", None, "blind correct", "Dark-control sentence (PP ¶2) does not state the atmosphere.")
A("PMC9295126", ["l", "m"], "catalyst_loading", {"v": 0.2, "loc": "Figure 3 caption", "s": "0.2 equiv of fluorenone"}, "blind correct",
  "Gram-scale runs: loading printed as 0.2 equiv (Figure 3 caption); equal to 20 mol% per repeat unit but recorded as printed.")
A("PMC9295126", ["l", "m"], "catalyst_loading_unit", {"v": "equiv", "inferred": "unit printed with the value (per styrene repeat unit)"}, "blind correct", "as printed")
for pm, rids in (("PMC10793207", ["b"]), ("PMC11796324", ["h"]), ("PMC13590609", list("abcdefghi"))):
    A(pm, rids, "catalyst", "__keep__", "equivalent", "Extraction 'none' and blind null both mean no catalyst; the extraction states it explicitly.")
A("PMC13590609", ["d", "e"], "solvent", "__keep__", "equivalent", "Same solvent; extraction lists the components of the paper's 'mixed Cl-Sol'.")
A("PMC13590609", ["d", "e"], "yield:terephthalic acid", "__keep__", "extraction correct",
  "Source paragraph: 1:1 ratio ~70% (record d); pre-formed OPP5 48.1% (record e). Blind tasks were aligned to different sentences of the same paragraph.")
A("PMC9295126", ["e", "f", "g", "h"], "products", "__keep__", "equivalent", "Controls: 0% benzoic acid; extraction names the product measured, blind listed no product formed.")


def main():
    log = []
    for pm, rids, field, new, decision, why in ADJ:
        p = EX / f"{pm}.json"
        d = json.loads(p.read_text())
        if field in ("concentration_note", "yield_alignment"):
            log.append({"pmcid": pm, "rids": "*" if rids == "*" else ";".join(rids), "field": field, "decision": decision, "rationale": why})
            continue
        targets = d["records"] if rids == "*" else [r for r in d["records"] if r["rid"] in rids]
        if new == "__keep__":
            log.append({"pmcid": pm, "rids": "*" if rids == "*" else ";".join(rids), "field": field, "decision": decision, "rationale": why})
            continue
        if rids == "*" and field in d.get("shared", {}):
            d["shared"][field] = new
        else:
            for r in targets:
                r.setdefault("fields", {})[field] = new
        for r in targets:
            tag = f"[adjudicated {field}: {decision}]"
            if tag not in r.get("notes", ""):
                r["notes"] = (r.get("notes", "") + " " + tag).strip()
        p.write_text(json.dumps(d, indent=1, ensure_ascii=False))
        log.append({"pmcid": pm, "rids": "*" if rids == "*" else ";".join(rids), "field": field, "decision": decision, "rationale": why})
    with open(LOG, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["pmcid", "rids", "field", "decision", "rationale"]); w.writeheader(); w.writerows(log)
    print(len(log), "adjudications logged")


if __name__ == "__main__":
    main()
