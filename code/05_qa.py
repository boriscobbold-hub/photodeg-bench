#!/usr/bin/env python3
"""Step 5 (Agent F): quality assurance report, exceptions file and the stats file.

Reads   data/processed/corpus.csv, data/curated/screening.csv, data/curated/screening_log.csv,
        data/curated/records.csv, data/curated/rejected_records.csv, data/curated/qa_flags.csv,
        data/curated/extractions/*.json, data/curated/verification/*,
        data/processed/photodeg_bench_v{version}.csv, data/processed/validation_report.txt
Writes  data/processed/qa_report.txt, data/processed/exceptions.csv, paper/stats.json

Checks: screening flow; schema validation result; source traceability (every field matched or
inferred with reason); independent blind agreement; unresolved disagreements; duplicate detection;
range and statistical-outlier checks (IQR within endpoint); cross-field consistency; controls that
show deconstruction; license distribution; risk-weighted and random spot-check lists.
Exit code 1 if a critical check fails.
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import json
import random
import statistics
import sys
from pathlib import Path

from common import CURATED, PAPER, PROCESSED, ROOT

V = CURATED / "verification"


def read(path):
    p = Path(path)
    if not p.exists():
        return []
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def iqr_outliers(vals):
    xs = sorted(v for _, v in vals)
    if len(xs) < 8:
        return []
    q1, q3 = statistics.quantiles(xs, n=4)[0], statistics.quantiles(xs, n=4)[2]
    lo, hi = q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)
    return [(k, v) for k, v in vals if v < lo or v > hi]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="1.0")
    ap.add_argument("--seed", type=int, default=20261012)
    a = ap.parse_args()

    corpus = read(PROCESSED / "corpus.csv")
    fetch = json.loads((PROCESSED / "fetch_stats.json").read_text()) if (PROCESSED / "fetch_stats.json").exists() else {}
    screening = read(CURATED / "screening.csv")
    slog = read(CURATED / "screening_log.csv")
    records = read(CURATED / "records.csv")
    rejected = read(CURATED / "rejected_records.csv")
    flags = read(CURATED / "qa_flags.csv")
    bench = read(PROCESSED / f"photodeg_bench_v{a.version}.csv")
    det = [json.loads(l) for l in open(V / "deterministic.jsonl", encoding="utf-8")] if (V / "deterministic.jsonl").exists() else []
    blind = read(V / "blind_comparison.csv")
    adjud = read(V / "adjudications.csv")
    sys.path.insert(0, str(ROOT / "code" / "curation"))
    import unresolved as UR
    unres = UR.unresolved() if (V / "adjudication_queue.csv").exists() else []
    val_text = (PROCESSED / "validation_report.txt").read_text() if (PROCESSED / "validation_report.txt").exists() else ""

    extractions = [json.loads(f.read_text()) for f in sorted((CURATED / "extractions").glob("*.json"))]
    excluded_obs = [(d["pmcid"], o) for d in extractions for o in d.get("excluded_observations", [])]

    codes = collections.Counter(l["code"] for l in slog)
    ft = sum(1 for l in slog if l.get("has_fulltext") == "y")
    in_scope_noft = sum(1 for l in slog if l["code"] == "E6" and l["stage"] != "full text")
    ft_assessed = sum(1 for l in slog if l["stage"] == "full text")
    included = [l for l in slog if l["code"] == "include"]

    critical, warn = [], []
    # traceability
    outcomes = collections.Counter(d["outcome"] for d in det)
    bad_fields = [d for d in det if d["outcome"] not in ("matched", "inferred")]
    if bad_fields:
        critical.append(f"{len(bad_fields)} fields fail the deterministic source check")
    if unres:
        critical.append(f"{len(unres)} unresolved verification disagreements")
    if "errors: 0" not in val_text:
        critical.append("schema validation has errors (see validation_report.txt)")
    not_blind = [r["record_id"] for r in bench if r.get("blind_verified") != "y"]
    if not_blind:
        critical.append(f"{len(not_blind)} released records lack independent verification")
    # duplicates
    keyf = lambda r: (r["doi"], r["polymer"], r["polymer_detail"], r["time"], r["temperature_c"], r["catalyst"], r["catalyst_loading"],  # noqa: E731
                      r["mn_before"], r["mn_after"], r["mw_before"], r["mw_after"], r["product_yields"], r["atmosphere"], r["solvent"], r["light_source"])
    dup = [k for k, n in collections.Counter(keyf(r) for r in bench).items() if n > 1]
    if dup:
        warn.append(f"{len(dup)} groups of records with identical keys (possible duplicates)")
    # ranges
    rng = []
    for r in bench:
        rf = fnum(r.get("retained_fraction"))
        if rf is not None and rf > 1.0:
            rng.append((r["record_id"], f"retained_fraction {rf:.3g} > 1 (molar mass increased)"))
        for part in (r.get("product_yields") or "").split(";"):
            if "%" in part:
                y = fnum(part.split(":")[-1].replace("%", "").strip())
                if y is not None and not 0 <= y <= 100:
                    rng.append((r["record_id"], f"yield out of range: {part.strip()}"))
        th = fnum(r.get("time_h"))
        if th is not None and (th <= 0 or th > 24 * 60):
            rng.append((r["record_id"], f"time_h {th}"))
        tc = fnum(r.get("temperature_c"))
        if tc is not None and not -80 <= tc <= 300:
            rng.append((r["record_id"], f"temperature_c {tc}"))
    # statistical outliers
    rf_vals = [(r["record_id"], fnum(r["retained_fraction"])) for r in bench if fnum(r.get("retained_fraction")) is not None and r["is_control"] == "n"]
    by_prod = collections.defaultdict(list)
    for r in bench:
        if r["is_control"] == "y":
            continue
        for part in (r.get("product_yields") or "").split(";"):
            if ":" in part and "%" in part:
                name, val = part.split(":", 1)
                v = fnum(val.replace("%", "").strip())
                if v is not None:
                    by_prod[name.strip()].append((r["record_id"], v))
    outliers = [(k, f"retained_fraction {v:.3g}") for k, v in iqr_outliers(rf_vals)]
    for prod, vals in by_prod.items():
        outliers += [(k, f"{prod} yield {v}") for k, v in iqr_outliers(vals)]
    # controls showing deconstruction
    ctrl_active = []
    for r in bench:
        if r["is_control"] != "y":
            continue
        rf = fnum(r.get("retained_fraction"))
        ys = [fnum(p.split(":")[-1].replace("%", "").strip()) for p in (r.get("product_yields") or "").split(";") if "%" in p]
        if (rf is not None and rf < 0.5) or any(y and y > 10 for y in ys):
            ctrl_active.append((r["record_id"], f"control shows deconstruction (retained {rf}, yields {r.get('product_yields')}): {r.get('notes', '')[:90]}"))
    # spot checks
    rnd = random.Random(a.seed)
    ids = [r["record_id"] for r in bench]
    rand5 = rnd.sample(ids, k=min(5, len(ids)))
    risk = sorted({r["record_id"] for r in bench if r.get("qa_flags")} | {k for k, _ in outliers} | {k for k, _ in ctrl_active} | {k for k, _ in rng})
    risk_unchecked = [k for k in risk if k in not_blind]
    if risk_unchecked:
        critical.append(f"{len(risk_unchecked)} high-risk records lack independent verification")

    blind_status = collections.Counter(b["status"] for b in blind)
    flag_counts = collections.Counter(f["flag"] for f in flags)
    lic = collections.Counter(r["source_license"] for r in bench)
    years = collections.Counter()
    yr = {s["paper_id"]: s["year"] for s in screening}
    for r in bench:
        years[yr.get(r["paper_id"], "")] += 1

    def cnt(col):
        return dict(collections.Counter((r.get(col) or "missing") for r in bench).most_common())

    completeness = {c: sum(1 for r in bench if (r.get(c) or "").strip() not in ("", "unknown", "not_reported"))
                    for c in ["primary_before", "primary_after", "sec_calibration", "catalyst", "catalyst_loading", "wavelength_nm",
                              "light_color", "irradiance", "solvent", "concentration", "atmosphere", "temperature_c", "time_h",
                              "product_yields", "yield_basis", "replicates", "yield_uncertainty"]}
    rf_sorted = sorted(v for _, v in rf_vals)
    stats = {
        "version": a.version, "built": dt.date.today().isoformat(),
        "n_corpus_papers": len(corpus) or fetch.get("n_unique_papers"), "n_corpus_europepmc": fetch.get("n_europepmc"),
        "n_corpus_openalex": fetch.get("n_openalex"), "n_screened": len(slog), "n_fulltext_available": ft,
        "screening_codes": dict(codes),
        "screening_codes_title_abstract": dict(collections.Counter(l["code"] for l in slog if l["stage"] != "full text")),
        "screening_codes_full_text": dict(collections.Counter(l["code"] for l in slog if l["stage"] == "full text")), "n_fulltext_assessed": ft_assessed, "n_included_papers": len(included),
        "n_in_scope_no_fulltext": in_scope_noft,
        "share_in_scope_lost_to_access": round(in_scope_noft / (in_scope_noft + ft_assessed), 3) if (in_scope_noft + ft_assessed) else None,
        "n_records_extracted": len(records) + len(rejected), "n_records_released": len(bench), "n_records_rejected": len(rejected),
        "n_excluded_observations": len(excluded_obs),
        "n_fields_checked": len(det), "field_outcomes": dict(outcomes),
        "blind_field_comparison": dict(blind_status), "n_adjudications": len(adjud), "n_unresolved": len(unres),
        "n_controls": sum(r["is_control"] == "y" for r in bench),
        "by_polymer_class": cnt("polymer_class"), "by_polymer": cnt("polymer"), "by_calibration_class": cnt("calibration_class"),
        "by_wavelength_band": cnt("wavelength_band"), "by_thermal_regime": cnt("thermal_regime"),
        "by_tier_molar_mass": cnt("tier_molar_mass"), "by_tier_product_yield": cnt("tier_product_yield"),
        "n_molar_mass_records": sum(1 for r in bench if r.get("retained_fraction")),
        "n_product_yield_records": sum(1 for r in bench if r.get("product_yields")),
        "retained_fraction_median_noncontrol": statistics.median(rf_sorted) if rf_sorted else None,
        "retained_fraction_min_noncontrol": rf_sorted[0] if rf_sorted else None,
        "retained_fraction_max_noncontrol": rf_sorted[-1] if rf_sorted else None,
        "records_by_publication_year": dict(sorted(years.items())), "source_licenses": dict(lic),
        "qa_flag_counts": dict(flag_counts), "field_completeness": completeness,
        "n_duplicate_groups": len(dup), "n_range_issues": len(rng), "n_outliers": len(outliers),
        "n_controls_showing_deconstruction": len(ctrl_active),
        "critical_failures": critical, "warnings": warn, "spot_check_seed": a.seed,
    }
    PAPER.mkdir(parents=True, exist_ok=True)
    (PAPER / "stats.json").write_text(json.dumps(stats, indent=1, ensure_ascii=False))

    ex = []
    for r in rejected:
        ex.append({"kind": "rejected_record", "id": r["record_id"], "detail": r.get("rejection_reason", "")})
    for pm, o in excluded_obs:
        ex.append({"kind": "excluded_observation", "id": pm, "detail": f"{o.get('what')}: {o.get('why')} [{o.get('loc', '')}]"})
    for k, why in rng + outliers + ctrl_active:
        ex.append({"kind": "flagged_value", "id": k, "detail": why})
    for f in flags:
        ex.append({"kind": f"qa_flag:{f['flag']}", "id": f["record_id"], "detail": f["evidence"]})
    for l in slog:
        if l["code"] == "ambiguous":
            ex.append({"kind": "ambiguous_paper", "id": l["paper_id"], "detail": l["rationale"]})
    for q in unres:
        ex.append({"kind": "unresolved_disagreement", "id": f"{q['pmcid']}-{q['rid']}", "detail": f"{q['field']}: {q['extracted']} vs {q['blind']}"})
    with open(PROCESSED / "exceptions.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["kind", "id", "detail"]); w.writeheader(); w.writerows(ex)

    L = []
    w = L.append
    w(f"PhotoDeg-Bench QA report  v{a.version}  built {stats['built']}")
    w("=" * 78)
    w(f"\nRESULT: {'PASS' if not critical else 'FAIL'}  ({len(critical)} critical, {len(warn)} warnings)")
    for c in critical:
        w(f"  CRITICAL  {c}")
    for c in warn:
        w(f"  warning   {c}")
    w("\n1. SCREENING FLOW (papers)")
    w(f"  corpus (unique; Europe PMC {stats['n_corpus_europepmc']}, OpenAlex {stats['n_corpus_openalex']})  {stats['n_corpus_papers']}")
    w(f"  passed automatic screen and year floor            {stats['n_screened']}")
    ta = stats["screening_codes_title_abstract"]
    for k in ("E1", "E2", "E3", "E4", "DUP"):
        w(f"    excluded {k:3s} on title/abstract                  {ta.get(k, 0)}")
    w(f"    in scope but no openly retrievable full text (E6)  {in_scope_noft}")
    w(f"  full text assessed                                 {ft_assessed}")
    w("    excluded at full text: " + ", ".join(f"{k} {v}" for k, v in sorted(stats["screening_codes_full_text"].items()) if k != "include"))
    w(f"  INCLUDED                                           {len(included)}")
    w(f"  share of in-scope papers lost to access            {stats['share_in_scope_lost_to_access']}")
    w("\n2. RECORDS")
    w(f"  extracted {stats['n_records_extracted']}, released {len(bench)}, rejected {len(rejected)}; controls {stats['n_controls']}")
    w(f"  observations seen but not recorded (with reasons)  {len(excluded_obs)}")
    w("\n3. VERIFICATION")
    w(f"  deterministic source check: {len(det)} fields -> {dict(outcomes)}")
    w(f"  independent blind re-extraction (field level): {dict(blind_status)}")
    w(f"  adjudications logged: {len(adjud)}; unresolved: {len(unres)}")
    w("  (agreement between AI passes is not treated as verification; every value is anchored by the source check)")
    w("\n4. COMPOSITION")
    for key in ("by_polymer", "by_calibration_class", "by_wavelength_band", "by_thermal_regime", "by_tier_molar_mass", "by_tier_product_yield"):
        w(f"  {key}: {stats[key]}")
    w(f"  source licenses: {dict(lic)}")
    w(f"  records by publication year: {stats['records_by_publication_year']}")
    w("\n5. COMPLETENESS (released records with a value)")
    for k, v in completeness.items():
        w(f"  {k:20s} {v:4d} / {len(bench)}")
    w("\n6. RANGE, OUTLIER AND CONSISTENCY CHECKS")
    w(f"  duplicates: {len(dup)}; range issues: {len(rng)}; IQR outliers: {len(outliers)}; controls showing deconstruction: {len(ctrl_active)}")
    for k, why in rng + outliers + ctrl_active:
        w(f"   - {k}: {why}")
    w("\n7. QA FLAGS (travel with each record)")
    for k, v in flag_counts.most_common():
        w(f"  {k:30s} {v}")
    w("\n8. SPOT CHECKS")
    w(f"  random (seed {a.seed}): {', '.join(rand5)}")
    w(f"  risk-weighted (flagged, outliers, active controls): {len(risk)} records, all independently re-extracted: {'yes' if not risk_unchecked else 'NO'}")
    w("\nexceptions: data/processed/exceptions.csv; numbers: paper/stats.json")
    (PROCESSED / "qa_report.txt").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 1 if critical else 0


if __name__ == "__main__":
    sys.exit(main())
