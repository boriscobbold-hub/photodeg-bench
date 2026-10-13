#!/usr/bin/env python3
"""Step 6 (Agent G): figures from the final validated data. DRAFT-stamped until --final.

Reads   data/processed/photodeg_bench_v{version}.csv, paper/stats.json
Writes  paper/figures/fig1_flow.{png,svg}            study selection flow (counts from stats.json)
        paper/figures/fig2_retained_vs_time.{png,svg} molar-mass retention vs irradiation time
        paper/figures/fig3_benzoic_acid.{png,svg}    benzoic acid yield from polystyrene, by study
        paper/figures/fig4_composition.{png,svg}     records by polymer and endpoint

Controls are excluded from fig2 and fig3 (they are performance figures). Every number shown comes
from the release table or stats.json.

Usage: python code/06_figures.py [--version 1.0] [--final] [--in FILE] [--out-dir DIR]
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["svg.hashsalt"] = "photodeg-bench"   # deterministic SVG ids
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

from common import PAPER, PROCESSED  # noqa: E402

SURFACE, TEXT, TEXT2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]   # validated all-pairs for scatter (dataviz reference palette)
CLASS_ORDER = ["vinyl_styrenic", "vinyl_methacrylate", "polyolefin"]
CLASS_LABEL = {"vinyl_styrenic": "polystyrene", "vinyl_methacrylate": "polymethacrylates", "polyolefin": "polypropylene"}


def style(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=TEXT2, labelsize=9)
    ax.grid(True, color=GRID, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)


def stamp(fig, final):
    if not final:
        fig.text(0.5, 0.5, "DRAFT", fontsize=64, color="#d0cfca", alpha=0.45, ha="center", va="center",
                 rotation=30, zorder=100, weight="bold")


def save(fig, out, name):
    fig.tight_layout()
    for ext in ("png", "svg"):
        meta = {"Date": None} if ext == "svg" else {"Software": None}
        fig.savefig(out / f"{name}.{ext}", dpi=200, facecolor=SURFACE, metadata=meta)
    plt.close(fig)


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def fig_flow(stats, out, final):
    c = stats["screening_codes_title_abstract"]
    cf = stats["screening_codes_full_text"]
    boxes = [
        (0.5, 0.92, f"Records found\nEurope PMC {stats['n_corpus_europepmc']} + OpenAlex {stats['n_corpus_openalex']}\n→ {stats['n_corpus_papers']} unique open-access papers"),
        (0.5, 0.72, f"Passed automatic screen and year floor (2010+)\n{stats['n_screened']}"),
        (0.5, 0.50, f"In scope by title/abstract (E1–E4)\n{stats['n_fulltext_assessed'] + c.get('E6', 0)}"),
        (0.25, 0.27, f"Full text assessed\n{stats['n_fulltext_assessed']}"),
        (0.25, 0.06, f"Included\n{stats['n_included_papers']} papers · {stats['n_records_released']} records"),
    ]
    side = [
        (0.83, 0.61, f"Excluded on title/abstract\nE1 review {c.get('E1', 0)} · E2 substrate {c.get('E2', 0)}\nE3 UV-only {c.get('E3', 0)} · E4 not photochemical {c.get('E4', 0)}"),
        (0.75, 0.27, f"No openly retrievable full text\n(E6, in scope) {c.get('E6', 0)}"),
        (0.75, 0.06, f"Excluded at full text\nE5 no benchmark endpoint {cf.get('E5', 0)}\nE6 values only in figures {cf.get('E6', 0)} · E4 {cf.get('E4', 0)}"),
    ]
    fig, ax = plt.subplots(figsize=(7.2, 6.4), facecolor=SURFACE)
    ax.set_axis_off()
    for x, y, t in boxes + side:
        ax.add_patch(FancyBboxPatch((x - 0.21, y - 0.065), 0.42, 0.13, boxstyle="round,pad=0.005,rounding_size=0.01",
                                    linewidth=1, edgecolor="#a3a29c", facecolor="white"))
        ax.text(x, y, t, ha="center", va="center", fontsize=8.3, color=TEXT)
    arrow = dict(arrowstyle="-|>", color=TEXT2, lw=1)
    for (x0, y0), (x1, y1) in [((0.5, 0.855), (0.5, 0.785)), ((0.5, 0.655), (0.5, 0.565)), ((0.42, 0.435), (0.27, 0.335)),
                               ((0.58, 0.435), (0.73, 0.335)), ((0.25, 0.205), (0.25, 0.125)), ((0.46, 0.27), (0.54, 0.10)),
                               ((0.62, 0.72), (0.70, 0.66))]:
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=arrow)
    ax.set_xlim(0, 1.05); ax.set_ylim(-0.02, 1)
    ax.set_title("PhotoDeg-Bench v1.0: study selection", loc="left", color=TEXT, fontsize=11)
    stamp(fig, final)
    save(fig, out, "fig1_flow")


def fig_retained(rows, out, final):
    pts = [(fnum(r["time_h"]), fnum(r["retained_fraction"]), r["polymer_class"], r["calibration_class"])
           for r in rows if r["is_control"] == "n"]
    pts = [p for p in pts if p[0] and p[1]]
    fig, ax = plt.subplots(figsize=(6.6, 4.4), facecolor=SURFACE)
    style(ax)
    for i, cls in enumerate(CLASS_ORDER):
        sel = [p for p in pts if p[2] == cls]
        if not sel:
            continue
        ax.scatter([p[0] for p in sel], [p[1] for p in sel], s=46, color=SERIES[i], edgecolor=SURFACE, linewidth=1.5,
                   zorder=3, label=f"{CLASS_LABEL[cls]} (n={len(sel)})")
    ax.axhline(1.0, color=TEXT2, linewidth=0.8, linestyle=(0, (3, 3)), zorder=2)
    ax.text(0.99, 1.0, "no change ", transform=ax.get_yaxis_transform(), va="bottom", ha="right", fontsize=8, color=TEXT2)
    ax.set_xscale("log"); ax.set_yscale("log")
    plain = matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}")
    for axis in (ax.xaxis, ax.yaxis):
        axis.set_major_formatter(plain); axis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.xaxis.set_major_locator(matplotlib.ticker.FixedLocator([1, 2, 5, 10, 20, 50, 100]))
    ax.set_xlabel("Irradiation time (h)", color=TEXT2, fontsize=9)
    ax.set_ylabel("Retained fraction of molar mass\n(after / before, same average and SEC method)", color=TEXT2, fontsize=9)
    ax.set_title("Molar-mass retention vs irradiation time (controls excluded)", loc="left", color=TEXT, fontsize=11)
    leg = ax.legend(fontsize=8, frameon=False, loc="lower left")
    for t in leg.get_texts():
        t.set_color(TEXT)
    stamp(fig, final)
    save(fig, out, "fig2_retained_vs_time")
    return len(pts)


def fig_benzoic(rows, out, final):
    by = collections.defaultdict(list)
    for r in rows:
        if r["is_control"] == "y" or r["polymer"] != "polystyrene":
            continue
        for part in (r["product_yields"] or "").split(";"):
            if ":" in part and part.split(":")[0].strip() == "benzoic acid" and "%" in part:
                v = fnum(part.split(":")[1].replace("%", "").strip())
                if v is not None:
                    by[r["doi"]].append(v)
    items = sorted(by.items(), key=lambda kv: (max(kv[1]), kv[0]))
    fig, ax = plt.subplots(figsize=(6.6, 0.55 * len(items) + 1.5), facecolor=SURFACE)
    style(ax)
    ax.grid(axis="y", visible=False)
    for i, (doi, vals) in enumerate(items):
        ax.plot([min(vals), max(vals)], [i, i], color=GRID, linewidth=2, zorder=2)
        ax.scatter(vals, [i] * len(vals), s=40, color=SERIES[0], edgecolor=SURFACE, linewidth=1.2, zorder=3)
        ax.text(max(vals), i, f"  max {max(vals):g}% (n={len(vals)})", va="center", fontsize=8, color=TEXT2)
    ax.set_yticks(range(len(items)), [d for d, _ in items], color=TEXT, fontsize=8)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Benzoic acid yield from polystyrene (%; basis as reported per study)", color=TEXT2, fontsize=9)
    ax.set_title("Benzoic acid from polystyrene, by study (non-control)", loc="left", color=TEXT, fontsize=11)
    stamp(fig, final)
    save(fig, out, "fig3_benzoic_acid")
    return sum(len(v) for v in by.values())


def fig_composition(rows, out, final):
    c_mm = collections.Counter(r["polymer"] for r in rows if r["retained_fraction"])
    c_py = collections.Counter(r["polymer"] for r in rows if r["product_yields"])
    polys = sorted(set(c_mm) | set(c_py), key=lambda p: (c_mm[p] + c_py[p], p))   # name breaks ties: deterministic
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 0.42 * len(polys) + 1.6), facecolor=SURFACE, sharey=True)
    for ax, c, title in ((axes[0], c_mm, "molar-mass records"), (axes[1], c_py, "product-yield records")):
        style(ax); ax.grid(axis="y", visible=False)
        vals = [c[p] for p in polys]
        ax.barh(range(len(polys)), vals, height=0.55, color=SERIES[0], zorder=3)
        for i, v in enumerate(vals):
            if v:
                ax.text(v, i, f" {v}", va="center", fontsize=8, color=TEXT2)
        ax.set_title(title, loc="left", color=TEXT, fontsize=10)
        ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
    axes[0].set_yticks(range(len(polys)), [p if len(p) < 34 else p[:32] + "…" for p in polys], color=TEXT, fontsize=8)
    fig.suptitle("PhotoDeg-Bench v1.0: records by polymer and endpoint (controls included)", x=0.01, ha="left", color=TEXT, fontsize=11)
    stamp(fig, final)
    save(fig, out, "fig4_composition")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="1.0")
    ap.add_argument("--final", action="store_true")
    ap.add_argument("--in", dest="inp")
    ap.add_argument("--out-dir", default=str(PAPER / "figures"))
    a = ap.parse_args()
    src = Path(a.inp) if a.inp else PROCESSED / f"photodeg_bench_v{a.version}.csv"
    with open(src, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    stats_path = PAPER / "stats.json"
    if stats_path.exists() and not a.inp:
        fig_flow(json.loads(stats_path.read_text()), out, a.final)
    n2 = fig_retained(rows, out, a.final)
    n3 = fig_benzoic(rows, out, a.final) if any(r.get("polymer") == "polystyrene" for r in rows) else 0
    fig_composition(rows, out, a.final)
    print(f"figures -> {out} ({'final' if a.final else 'DRAFT'}); fig2 points {n2}; fig3 points {n3}")


if __name__ == "__main__":
    main()
