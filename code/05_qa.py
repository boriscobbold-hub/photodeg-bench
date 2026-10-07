#!/usr/bin/env python3
"""Step 5: QA report and the stats file every document reads its numbers from.

Reads   data/processed/corpus.csv, data/curated/screening.csv, data/curated/records.csv,
        data/processed/photodeg_bench_v{version}.csv, data/processed/harmonization_log.csv
Writes  data/processed/qa_report.txt
        paper/stats.json

Spot checks: the report names records for the curator to re-check against the source by hand:
five random (seeded), the five largest and five smallest retained fractions, and every record
whose molar mass rose.

Usage
  python code/05_qa.py [--version 1.0] [--seed 20261007]
"""

from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import json
import random
from pathlib import Path

from common import CURATED, PAPER, PROCESSED, ROOT


def read(path):
    if not Path(path).exists():
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", default="1.0")
    ap.add_argument("--seed", type=int, default=20261007)
    ap.add_argument("--processed", default=str(PROCESSED))
    ap.add_argument("--curated", default=str(CURATED))
    ap.add_argument("--stats", default=str(PAPER / "stats.json"))
    a = ap.parse_args()
    P, C = Path(a.processed), Path(a.curated)

    corpus = read(P / "corpus.csv")
    screening = read(C / "screening.csv")
    records = read(C / "records.csv")
    bench = read(P / f"photodeg_bench_v{a.version}.csv")
    hlog = read(P / "harmonization_log.csv")
    fetch_stats = json.loads((P / "fetch_stats.json").read_text()) if (P / "fetch_stats.json").exists() else {}

    included = [s for s in screening if s.get("include", "").strip().lower() in ("y", "yes")]
    excluded = [s for s in screening if s.get("include", "").strip().lower() in ("n", "no")]
    undecided = [s for s in screening if s.get("include", "").strip() == ""]
    excl_reasons = collections.Counter((s.get("exclusion_reason") or "unspecified").strip() for s in excluded)
    papers_with_records = {r["paper_id"] for r in records}
    bench_papers = {r["paper_id"] for r in bench}
    dropped = collections.Counter(l["rule"] for l in hlog if l["action"].startswith("excluded"))

    rf = [(r["record_id"], fnum(r.get("retained_fraction"))) for r in bench if fnum(r.get("retained_fraction")) is not None]
    rf_vals = sorted(v for _, v in rf)
    rose = [r["record_id"] for r in bench if fnum(r.get("retained_fraction")) is not None and fnum(r["retained_fraction"]) > 1]

    def counts(col):
        return dict(collections.Counter((r.get(col) or "missing") for r in bench).most_common())

    completeness = {}
    for col in ["primary_before", "primary_after", "sec_calibration", "catalyst", "wavelength_nm", "wavelength_band",
                "irradiance", "solvent", "time_h", "products", "product_yields"]:
        completeness[col] = sum(1 for r in bench if (r.get(col) or "").strip() not in ("", "unknown"))

    rnd = random.Random(a.seed)
    sample = rnd.sample([r["record_id"] for r in bench], k=min(5, len(bench))) if bench else []
    by_rf = sorted(rf, key=lambda t: t[1])

    stats = {
        "version": a.version,
        "built": dt.date.today().isoformat(),
        "n_corpus_papers": len(corpus) or fetch_stats.get("n_unique_papers"),
        "n_corpus_europepmc": fetch_stats.get("n_europepmc"),
        "n_corpus_openalex": fetch_stats.get("n_openalex"),
        "n_auto_screen_pass": len(screening),
        "n_fulltext": fetch_stats.get("n_fulltext"),
        "n_included_papers": len(included),
        "n_excluded_papers": len(excluded),
        "n_undecided_papers": len(undecided),
        "exclusion_reasons": dict(excl_reasons),
        "n_curated_records": len(records),
        "n_papers_with_records": len(papers_with_records),
        "n_benchmark_records": len(bench),
        "n_benchmark_papers": len(bench_papers),
        "records_dropped_by_rule": dict(dropped),
        "by_polymer_class": counts("polymer_class"),
        "by_polymer": counts("polymer"),
        "by_calibration_class": counts("calibration_class"),
        "by_wavelength_band": counts("wavelength_band"),
        "by_tier": counts("tier"),
        "n_controls": sum(r.get("is_control") == "y" for r in bench),
        "n_with_retained_fraction": len(rf_vals),
        "retained_fraction_median": rf_vals[len(rf_vals) // 2] if rf_vals else None,
        "retained_fraction_min": rf_vals[0] if rf_vals else None,
        "retained_fraction_max": rf_vals[-1] if rf_vals else None,
        "n_mass_increase": len(rose),
        "field_completeness": completeness,
        "spot_check_seed": a.seed,
    }
    Path(a.stats).parent.mkdir(parents=True, exist_ok=True)
    Path(a.stats).write_text(json.dumps(stats, indent=1))

    L = []
    w = L.append
    w(f"PhotoDeg-Bench QA report  v{a.version}  built {stats['built']}")
    w("=" * 72)
    w("\n1. FLOW (papers)")
    w(f"  corpus (unique, both sources)        {stats['n_corpus_papers']}")
    w(f"    from Europe PMC / OpenAlex          {stats['n_corpus_europepmc']} / {stats['n_corpus_openalex']}")
    w(f"  passed auto-screen + year scope       {stats['n_auto_screen_pass']}")
    w(f"  with OA JATS full text                {stats['n_fulltext']}")
    w(f"  curator: included / excluded / open   {len(included)} / {len(excluded)} / {len(undecided)}")
    for k, v in excl_reasons.most_common():
        w(f"      excluded: {k:30s} {v}")
    w(f"  included papers with >=1 record       {len(papers_with_records & {s['paper_id'] for s in included})}")
    w("\n2. FLOW (records)")
    w(f"  curated records                       {len(records)}")
    w(f"  in benchmark table                    {len(bench)}  (from {len(bench_papers)} papers)")
    for k, v in dropped.most_common():
        w(f"      dropped by {k:24s} {v}")
    if included and len(papers_with_records) < len(included):
        missing = sorted({s['paper_id'] for s in included} - papers_with_records)
        w(f"  included papers with NO records ({len(missing)}): " + ", ".join(missing[:30]) + (" ..." if len(missing) > 30 else ""))
    w("\n3. COMPOSITION")
    for key in ("by_polymer_class", "by_calibration_class", "by_wavelength_band", "by_tier"):
        w(f"  {key}")
        for k, v in stats[key].items():
            w(f"      {k:32s} {v}")
    w("\n4. COMPLETENESS (benchmark records with a value)")
    for k, v in completeness.items():
        w(f"  {k:24s} {v:5d} / {len(bench)}")
    w("\n5. RANGE CHECKS")
    w(f"  retained fraction: n={len(rf_vals)} min={stats['retained_fraction_min']} median={stats['retained_fraction_median']} max={stats['retained_fraction_max']}")
    w(f"  records where molar mass rose (retained > 1): {len(rose)} {rose[:20]}")
    for r in bench:
        th = fnum(r.get("time_h"))
        if th is not None and th > 24 * 30:
            w(f"  long irradiation (>30 d): {r['record_id']} {th:.0f} h")
    w("\n6. SPOT CHECKS for the curator (re-check each against the source by hand)")
    w(f"  random (seed {a.seed}): {', '.join(sample) or '-'}")
    w(f"  lowest retained fraction:  {', '.join(i for i, _ in by_rf[:5]) or '-'}")
    w(f"  highest retained fraction: {', '.join(i for i, _ in by_rf[-5:]) or '-'}")
    w(f"  mass increased:            {', '.join(rose[:5]) or '-'}")
    w("\n(stats written to paper/stats.json)")
    (P / "qa_report.txt").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
