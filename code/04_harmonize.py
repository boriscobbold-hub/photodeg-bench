#!/usr/bin/env python3
"""Step 4: apply the curator's harmonization rules to validated records.

Reads   rules/harmonization.yaml, data/curated/records.csv
Writes  data/processed/photodeg_bench_v{version}.csv   the benchmark table
        data/processed/harmonization_log.csv           one line per record per rule that changed something

Refuses to run while any required rule is unset or while 03_validate.py reports errors.
The code executes rules; it does not choose them.

Usage
  python code/04_harmonize.py
  python code/04_harmonize.py --rules tests/fixtures/synthetic_rules.yaml --records tests/fixtures/synthetic_records.csv --out-dir /tmp/x
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
from pathlib import Path

from common import CURATED, PROCESSED, ROOT, load_yaml

TO_G_PER_MOL = {"g/mol": 1.0, "Da": 1.0, "kg/mol": 1000.0, "kDa": 1000.0}
TO_H = {"s": 1 / 3600, "min": 1 / 60, "h": 1.0, "d": 24.0}


class RuleError(SystemExit):
    pass


def check_rules(rules: dict):
    r = rules["rules"]
    unset = [k for k, v in r.items() if v.get("required") and v.get("status") != "set"]
    if r["R03_calibration_policy"].get("decision") == "universal_conversion" and r["R04_mark_houwink_constants"].get("status") != "set":
        unset.append("R04_mark_houwink_constants (required because R03 = universal_conversion)")
    if unset:
        raise RuleError("Harmonization refused: these rules are not set by the curator:\n  - " + "\n  - ".join(unset)
                        + "\nEdit rules/harmonization.yaml (status: set, decision, rationale).")
    for k, v in r.items():
        if v.get("status") == "set" and "options" in v and isinstance(v.get("decision"), str) and v["decision"] not in v["options"]:
            raise RuleError(f"{k}: decision '{v['decision']}' is not one of the implemented options {v['options']}")


def f(x):
    x = (x or "").strip()
    return float(x) if x else None


def convert_mass(v, unit, target):
    if v is None or not unit:
        return None
    return v * TO_G_PER_MOL[unit] / TO_G_PER_MOL[target]


def mh_lookup(table, polymer, eluent, temp):
    for row in table:
        if row["polymer"].lower() == (polymer or "").lower() and row["eluent"].lower() == (eluent or "").lower() \
                and (row.get("temperature_c") is None or temp is None or abs(float(row["temperature_c"]) - temp) <= 5):
            if row.get("K") is not None and row.get("a") is not None:
                return float(row["K"]), float(row["a"])
    return None


def universal_convert(m_std, std_poly, analyte, eluent, temp, table):
    """Universal calibration: [eta]M equal at equal elution volume.
    M_X = ((K_S / K_X) * M_S^(1 + a_S)) ** (1 / (1 + a_X)). Masses in g/mol."""
    s = mh_lookup(table, std_poly, eluent, temp)
    x = mh_lookup(table, analyte, eluent, temp)
    if not s or not x:
        return None
    (ks, as_), (kx, ax) = s, x
    return ((ks / kx) * m_std ** (1 + as_)) ** (1 / (1 + ax))


STD_OF = {"conventional_PS": "polystyrene", "conventional_PMMA": "poly(methyl methacrylate)", "conventional_PEG_PEO": "PEG/PEO"}


def harmonize(records, rules):
    R = rules["rules"]
    unit = R["R01_canonical_mass_unit"]["decision"]
    primary_rule = R["R02_primary_average"]["decision"]
    cal_policy = R["R03_calibration_policy"]["decision"]
    mh_table = R["R04_mark_houwink_constants"].get("table") or []
    cal_map = R["R05_calibration_type_map"]["decision"] or {}
    metrics = R["R06_deconstruction_metrics"]["decision"] or []
    primary_metric = R["R06_deconstruction_metrics"].get("primary")
    same_basis = R["R07_same_basis_requirement"]["decision"]
    win = R["R08_visible_window"]
    bands = R["R09_wavelength_bands"].get("bands") or []
    color_only = R["R09_wavelength_bands"].get("color_only_reports")
    t_unit = R["R10_time_unit"]["decision"]
    tiers_mm = R["R11_comparability_tiers"].get("tiers_molar_mass") or R["R11_comparability_tiers"].get("tiers") or []
    tiers_py = R["R11_comparability_tiers"].get("tiers_product_yield") or []
    thermal = (R.get("R15_thermal_regime") or {}).get("decision") or {}
    controls = R["R13_controls_and_negatives"]["decision"]
    lic = R["R14_source_license_policy"]

    out, log = [], []

    def note(rid, rule, msg):
        log.append({"record_id": rid, "rule": rule, "action": msg})

    for r in records:
        rid = r["record_id"]
        # R14: license gate
        L = (r.get("source_license") or "").strip().lower().replace(" ", "-").replace("_", "-")
        if L in ("", "unknown"):
            if lic.get("unknown_license") != "include":
                note(rid, "R14", "excluded: unknown source license")
                continue
        elif L not in [x.lower() for x in lic.get("allowed") or []]:
            note(rid, "R14", f"excluded: license {L} not in allowed list")
            continue
        # R13: controls
        is_control = (r.get("is_control") or "").strip().lower() == "y" or (r.get("notes") or "").lower().startswith("control")
        if is_control and controls == "exclude":
            note(rid, "R13", "excluded: control run")
            continue

        h = dict(r)
        h["is_control"] = "y" if is_control else "n"

        # R01: masses to canonical unit
        for side in ("before", "after"):
            u = (r.get(f"mass_unit_{side}") or "").strip()
            for k in ("mn", "mw", "mp"):
                h[f"{k}_{side}_h"] = convert_mass(f(r.get(f"{k}_{side}")), u, unit) if u else None
        h["mass_unit_h"] = unit

        # R05: calibration class (may depend on whether standard matches the polymer)
        cal = (r.get("sec_calibration") or "not_reported").strip()
        cls = cal_map.get(cal, "unknown")
        if isinstance(cls, dict):  # e.g. {matched_if_polymer: polystyrene, matched: ..., otherwise: ...}
            match_poly = (cls.get("matched_if_polymer") or "").lower()
            cls = cls.get("matched") if (r.get("polymer") or "").lower() == match_poly else cls.get("otherwise")
        h["calibration_class"] = cls or "unknown"
        if not any((r.get(f"{k}_{sd}") or "").strip() for k in ("mn", "mw", "mp") for sd in ("before", "after")):
            h["calibration_class"] = "not_applicable"

        # R03: calibration policy for mismatched conventional values
        mismatched = h["calibration_class"] == "mismatched_conventional"
        h["mass_basis"] = "as_reported"
        if mismatched:
            if cal_policy == "exclude_mismatched":
                for side in ("before", "after"):
                    for k in ("mn", "mw", "mp"):
                        h[f"{k}_{side}_h"] = None
                h["mass_basis"] = "excluded_mismatched"
                note(rid, "R03", "mismatched calibration: harmonized masses cleared")
            elif cal_policy == "universal_conversion":
                std = STD_OF.get(cal)
                temp = f(r.get("sec_temperature_c"))
                ok = True
                for side in ("before", "after"):
                    for k in ("mn", "mw", "mp"):
                        v = h[f"{k}_{side}_h"]
                        if v is None:
                            continue
                        g = convert_mass(v, unit, "g/mol")
                        conv = universal_convert(g, std, r.get("polymer"), r.get("sec_eluent"), temp, mh_table) if std else None
                        if conv is None:
                            ok = False
                            h[f"{k}_{side}_h"] = None
                        else:
                            h[f"{k}_{side}_h"] = convert_mass(conv, "g/mol", unit)
                h["mass_basis"] = "universal_conversion" if ok else "conversion_unavailable"
                note(rid, "R03", h["mass_basis"])
            else:
                h["mass_basis"] = "relative_mismatched"

        # R02 + R07: primary average with a comparable before/after pair
        order = {"Mn_only": ["mn"], "Mn_then_Mw": ["mn", "mw"], "Mw_only": ["mw"], "Mp_only": ["mp"]}[primary_rule]
        h["primary_average"], pb, pa = "", None, None
        for k in order:
            b, a = h[f"{k}_before_h"], h[f"{k}_after_h"]
            if b is not None and a is not None:
                h["primary_average"], pb, pa = {"mn": "Mn", "mw": "Mw", "mp": "Mp"}[k], b, a
                break
        if pb is not None and same_basis == "same_average_same_calibration" and h["mass_basis"] in ("conversion_unavailable", "excluded_mismatched"):
            pb = pa = None
            h["primary_average"] = ""
        h["primary_before"], h["primary_after"] = pb, pa

        # R06: metrics
        if pb and pa:
            if "retained_fraction" in metrics:
                h["retained_fraction"] = pa / pb
            if "percent_reduction" in metrics:
                h["percent_reduction"] = 100 * (1 - pa / pb)
        mnb, mna = h["mn_before_h"], h["mn_after_h"]
        if "scissions_per_chain" in metrics and mnb and mna and h["primary_average"] == "Mn":
            h["scissions_per_chain"] = mnb / mna - 1
        h["primary_metric"] = primary_metric

        # R08 + R09: light window and band
        wl = f(r.get("wavelength_nm"))
        wr = (r.get("wavelength_range_nm") or "").strip()
        src = (r.get("light_source") or "").lower()
        color = (r.get("light_color") or "").strip().lower()
        in_window, flags = True, []
        lo, hi = win.get("lower_nm"), win.get("upper_nm")
        if wl is not None and lo is not None and hi is not None and not lo <= wl <= hi:
            in_window = False
        if wr:
            a_, b_ = (int(x) for x in wr.split("-"))
            if a_ < (lo or 0):
                flags.append("uv_component")
            if b_ - a_ > 150:
                flags.append("broadband")
        if color in ("white", "solar"):
            flags.append("broadband")
        if any(s in src for s in ("sun", "solar", "am1.5", "am 1.5", "xenon", "xe lamp")):
            flags.append("solar_or_xenon")
        policies = {"broadband": win.get("broadband_sources"), "solar_or_xenon": win.get("sunlight_or_solar_sim"),
                    "uv_component": win.get("uv_component_present")}
        if not in_window or any(policies.get(fl) == "exclude" for fl in flags):
            note(rid, "R08", f"excluded: outside visible window or excluded source ({','.join(flags) or wl})")
            continue
        h["light_flags"] = ";".join(sorted(set(flags)))
        band = ""
        if wl is not None:
            for bd in bands:
                if bd["lower_nm"] is not None and bd["upper_nm"] is not None and bd["lower_nm"] <= wl < bd["upper_nm"]:
                    band = bd["name"]
        elif color and color_only == "map_by_name" and any(bd["name"] == color for bd in bands):
            band = color
        if src.startswith("none") or "dark" in src:
            band = "dark"
        if not band and ("broadband" in flags or "solar_or_xenon" in flags):
            band = "broadband"
        h["wavelength_band"] = band or "unknown"

        # R15: thermal regime
        tc = f(r.get("temperature_c"))
        if tc is None:
            h["thermal_regime"] = "not_reported"
        elif tc < thermal.get("ambient_max_c", 60):
            h["thermal_regime"] = "ambient"
        elif tc <= thermal.get("heated_max_c", 120):
            h["thermal_regime"] = "heated"
        else:
            h["thermal_regime"] = "high_temperature"

        # R10: time
        t, tu = f(r.get("time")), (r.get("time_unit") or "").strip()
        h["time_h"] = t * TO_H[tu] / TO_H[t_unit] if t is not None and tu else None
        h["time_unit_h"] = t_unit

        # R11: tiers
        conds = {
            "has_primary_before_after": pb is not None and pa is not None,
            "has_wavelength": wl is not None or bool(wr),
            "has_irradiance": f(r.get("irradiance")) is not None,
            "has_time": h["time_h"] is not None,
            "has_catalyst": bool((r.get("catalyst") or "").strip()),
            "has_solvent": bool((r.get("solvent") or "").strip()),
            "has_products": bool((r.get("products") or "").strip()),
            "has_yield": bool((r.get("product_yields") or "").strip()),
            "has_yield_basis": bool((r.get("yield_basis") or "").strip()),
        }

        def tier_of(ladder):
            for tier in ladder:
                ok = (not tier.get("calibration_class_in") or h["calibration_class"] in tier["calibration_class_in"]) \
                    and all(conds.get(c, False) for c in tier.get("require") or [])
                if ok:
                    return tier["name"]
            return ""
        h["tier_molar_mass"] = tier_of(tiers_mm) if conds["has_primary_before_after"] else ""
        h["tier_product_yield"] = tier_of(tiers_py) if conds["has_yield"] else ""
        h["tier"] = h["tier_molar_mass"] or h["tier_product_yield"] or "unranked"
        out.append(h)
    return out, log


RELEASE_COLUMNS = [
    "record_id", "paper_id", "doi", "pmcid", "source_license", "locator", "is_control",
    "polymer", "polymer_class", "polymer_detail",
    "mn_before", "mw_before", "mp_before", "disp_before", "mass_unit_before",
    "mn_after", "mw_after", "mp_after", "disp_after", "mass_unit_after",
    "mn_before_h", "mw_before_h", "mp_before_h", "mn_after_h", "mw_after_h", "mp_after_h", "mass_unit_h",
    "sec_calibration", "calibration_class", "mass_basis", "sec_detector", "sec_eluent", "sec_temperature_c",
    "primary_average", "primary_before", "primary_after", "primary_metric",
    "retained_fraction", "percent_reduction",
    "catalyst", "catalyst_loading", "catalyst_loading_unit", "cocatalyst_additives",
    "light_source", "wavelength_nm", "wavelength_range_nm", "light_color", "wavelength_band", "light_flags",
    "irradiance", "irradiance_unit",
    "solvent", "concentration", "concentration_unit", "atmosphere", "temperature_c", "thermal_regime",
    "time", "time_unit", "time_h", "time_unit_h",
    "products", "product_yields", "yield_basis", "yield_uncertainty", "replicates",
    "tier_molar_mass", "tier_product_yield", "qa_flags",
    "extraction_method", "extractor", "source_verified", "blind_verified", "notes", "curator", "curation_date",
]


def fmt(v):
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:.6g}"
    return v


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rules", default=str(ROOT / "rules" / "harmonization.yaml"))
    ap.add_argument("--records", default=str(CURATED / "records.csv"))
    ap.add_argument("--out-dir", default=str(PROCESSED))
    ap.add_argument("--version", default="1.0")
    a = ap.parse_args()

    rules = load_yaml(Path(a.rules))
    check_rules(rules)
    with open(a.records, encoding="utf-8") as fh:
        records = list(csv.DictReader(fh))

    spec = importlib.util.spec_from_file_location("validate", Path(__file__).parent / "03_validate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    errs, _ = mod.validate(records, [])
    if errs:
        raise SystemExit(f"Harmonization refused: {len(errs)} validation errors. Run code/03_validate.py first.")

    out, log = harmonize(records, rules)
    od = Path(a.out_dir)
    od.mkdir(parents=True, exist_ok=True)
    path = od / f"photodeg_bench_v{a.version}.csv"
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=RELEASE_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for h in out:
            w.writerow({k: fmt(h.get(k)) for k in RELEASE_COLUMNS})
    with open(od / "harmonization_log.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["record_id", "rule", "action"])
        w.writeheader()
        w.writerows(log)
    print(f"{len(records)} records in, {len(out)} harmonized -> {path}; {len(log)} rule actions logged")


if __name__ == "__main__":
    main()
