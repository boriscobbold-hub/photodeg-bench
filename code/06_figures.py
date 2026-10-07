#!/usr/bin/env python3
"""Step 6: benchmark figures, stamped DRAFT until run with --final.

Reads   data/processed/photodeg_bench_v{version}.csv
Writes  paper/figures/fig1_composition.{png,svg}
        paper/figures/fig2_retained_vs_time.{png,svg}

Fig 1  records per polymer class (one hue; magnitude only)
Fig 2  retained fraction of the primary molar-mass average vs irradiation time, both log
       scaled, coloured by calibration class (at most three classes get colour; the rest are
       grey), controls drawn as open markers.

Usage
  python code/06_figures.py [--version 1.0] [--final] [--in FILE] [--out-dir DIR]
"""

from __future__ import annotations

import argparse
import collections
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402

from common import PAPER, PROCESSED  # noqa: E402

# Reference palette (dataviz skill), light mode
SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT2 = "#52514e"
GRID = "#e4e3df"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]   # first three slots: validated for all-pairs (scatter)
OTHER = "#a3a29c"
CLASS_ORDER = ["absolute", "matched_conventional", "mismatched_conventional"]


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


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def fig_composition(rows, out, final, version):
    c = collections.Counter(r.get("polymer_class") or "unspecified" for r in rows)
    items = sorted(c.items(), key=lambda t: t[1])
    fig, ax = plt.subplots(figsize=(6.4, 0.45 * len(items) + 1.4), facecolor=SURFACE)
    style(ax)
    ax.grid(axis="y", visible=False)
    y = range(len(items))
    ax.barh(list(y), [v for _, v in items], height=0.55, color=SERIES[0], zorder=3)
    ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
    ax.set_yticks(list(y), [k.replace("_", " ") for k, _ in items], color=TEXT)
    for i, (_, v) in enumerate(items):
        ax.text(v, i, f" {v}", va="center", ha="left", fontsize=9, color=TEXT2)
    ax.set_xlabel("Benchmark records", color=TEXT2, fontsize=9)
    ax.set_title(f"PhotoDeg-Bench v{version}: records by polymer class", loc="left", color=TEXT, fontsize=11)
    stamp(fig, final)
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(out / f"fig1_composition.{ext}", dpi=200, facecolor=SURFACE)
    plt.close(fig)


def fig_retained(rows, out, final, version):
    pts = [(fnum(r.get("time_h")), fnum(r.get("retained_fraction")), r.get("calibration_class") or "unknown",
            r.get("is_control") == "y") for r in rows]
    pts = [p for p in pts if p[0] and p[1]]
    fig, ax = plt.subplots(figsize=(6.4, 4.4), facecolor=SURFACE)
    style(ax)
    present = [c for c in CLASS_ORDER if any(p[2] == c for p in pts)]
    colors = {c: SERIES[i] for i, c in enumerate(CLASS_ORDER)}
    groups = present + (["other"] if any(p[2] not in CLASS_ORDER for p in pts) else [])
    for g in groups:
        sel = [p for p in pts if (p[2] == g if g != "other" else p[2] not in CLASS_ORDER)]
        col = colors.get(g, OTHER)
        filled = [p for p in sel if not p[3]]
        ctrl = [p for p in sel if p[3]]
        label = g.replace("_", " ")
        if filled:
            ax.scatter([p[0] for p in filled], [p[1] for p in filled], s=42, color=col, edgecolor=SURFACE,
                       linewidth=1.5, zorder=3, label=label)
        if ctrl:
            ax.scatter([p[0] for p in ctrl], [p[1] for p in ctrl], s=42, facecolor="none", edgecolor=col,
                       linewidth=1.5, zorder=3, label=f"{label} (control)")
    ax.axhline(1.0, color=TEXT2, linewidth=0.8, linestyle=(0, (3, 3)), zorder=2)
    ax.set_xscale("log")
    ax.set_yscale("log")
    plain = matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}")
    for axis in (ax.xaxis, ax.yaxis):
        axis.set_major_formatter(plain)
        axis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.text(0.99, 1.0, "no change ", transform=ax.get_yaxis_transform(), va="bottom", ha="right", fontsize=8, color=TEXT2)
    ax.set_xlabel("Irradiation time (h)", color=TEXT2, fontsize=9)
    ax.set_ylabel("Retained fraction of primary molar-mass average\n(after / before)", color=TEXT2, fontsize=9)
    ax.set_title(f"PhotoDeg-Bench v{version}: molar-mass retention vs time", loc="left", color=TEXT, fontsize=11)
    if groups:
        leg = ax.legend(title="SEC calibration class", fontsize=8, title_fontsize=8, frameon=False, loc="lower left")
        for t in leg.get_texts():
            t.set_color(TEXT)
        leg.get_title().set_color(TEXT2)
    stamp(fig, final)
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(out / f"fig2_retained_vs_time.{ext}", dpi=200, facecolor=SURFACE)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", default="1.0")
    ap.add_argument("--final", action="store_true", help="remove the DRAFT stamp (only after the verification gate)")
    ap.add_argument("--in", dest="inp")
    ap.add_argument("--out-dir", default=str(PAPER / "figures"))
    a = ap.parse_args()
    src = Path(a.inp) if a.inp else PROCESSED / f"photodeg_bench_v{a.version}.csv"
    with open(src, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    fig_composition(rows, out, a.final, a.version)
    fig_retained(rows, out, a.final, a.version)
    print(f"figures -> {out} ({'final' if a.final else 'DRAFT'})")


if __name__ == "__main__":
    main()
