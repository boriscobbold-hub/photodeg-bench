#!/usr/bin/env python3
"""Print an evidence pack for one paper: every text block or table whose content matters to the
benchmark, labelled with the exact locator that parse_jats() produces. Locators printed here are the
ones records must cite; verify_records.py re-parses the same XML and checks values at those locators.

Usage: python code/curation/evidence_pack.py <PMCID> [--all] [--max-chars N]
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code"))
import importlib.util  # noqa: E402

_s = importlib.util.spec_from_file_location("x", ROOT / "code" / "02_extract.py")
X = importlib.util.module_from_spec(_s)
_s.loader.exec_module(X)

KEY = re.compile(r"\bM\s?[nwp]\b|M_[nwp]|molecular weight|molar mass|\bGPC\b|\bSEC\b|size.exclusion|gel permeation|"
                 r"dispersity|\bĐ\b|\bPDI\b|yield|conversion|selectivit|\bnm\b|LED|lamp|irradiat|Kessil|sunlight|solar|"
                 r"depolymeri|degrad|monomer recovery|benzoic|mmol|mol ?%|wt ?%", re.I)


def blocks(pmcid):
    path = ROOT / "data" / "raw" / "fulltext" / f"{pmcid}.xml"
    for loc, kind, payload in X.parse_jats(path):
        if kind == "text":
            yield loc, payload
        else:
            header, rows = payload
            lines = [" | ".join(header)] + [f"r{i + 1}: " + " | ".join(r) for i, r in enumerate(rows)]
            yield loc + " [TABLE]", "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pmcid")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--max-chars", type=int, default=1800)
    a = ap.parse_args()
    for loc, text in blocks(a.pmcid):
        if not text:
            continue
        text = re.sub(r"\s+", " ", text) if "[TABLE]" not in loc else text
        if not a.all and re.match(r"(?i)(introduction|background|conclusions?|outlook|summary|abstract|title)\b", loc):
            continue
        if a.all or "[TABLE]" in loc or KEY.search(text):
            t = text if len(text) <= a.max_chars else text[: a.max_chars] + " …[truncated]"
            print(f"\n<<{loc}>>\n{t}")


if __name__ == "__main__":
    main()
