#!/usr/bin/env python3
"""Agent D, independent half (step 1): write blind verification tasks.

For each included record the task gives only an anchor (paper, primary locator, polymer, control flag)
and the list of field NAMES to report. No extracted values, no per-field locators, no notes. An
independent agent reads the article and fills the values; compare_blind.py then compares them.

Usage: python code/curation/blind_slots.py   -> data/curated/verification/slots/<PMCID>.json
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKIP = {"polymer_class", "light_color"}   # classifications, compared deterministically elsewhere


def main():
    out = ROOT / "data/curated/verification/slots"
    out.mkdir(parents=True, exist_ok=True)
    for f in sorted((ROOT / "data/curated/extractions").glob("*.json")):
        d = json.loads(f.read_text())
        if d["screen"]["decision"] != "include":
            continue
        tasks = []
        for r in d["records"]:
            fields = {**d.get("shared", {}), **r.get("fields", {})}
            names = sorted(k for k, v in fields.items() if v is not None and k not in SKIP and k != "product_yields")
            yields = [y["product"] for y in fields.get("product_yields") or []]
            tasks.append({"rid": r["rid"], "primary_loc": r.get("primary_loc"),
                          "polymer_anchor": (fields.get("polymer") or {}).get("v"),
                          "is_control": bool(r.get("is_control")),
                          "report_fields": names, "report_yields_for_products": yields})
        (out / f"{d['pmcid']}.json").write_text(json.dumps({"pmcid": d["pmcid"], "doi": d["doi"], "tasks": tasks}, indent=1))
        print(d["pmcid"], len(tasks))


if __name__ == "__main__":
    main()
