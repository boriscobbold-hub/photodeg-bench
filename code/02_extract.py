#!/usr/bin/env python3
"""Step 2: propose candidate values from each included paper's JATS full text.

Reads   data/curated/screening.csv (papers with include = y; or every auto-passed paper
        with --all-screened before screening is done)
Writes  data/processed/candidates.jsonl      one candidate per line, with a locator
        data/processed/review_sheet.csv      per-paper digest for the curator
        data/curated/records.csv             created with headers only if absent; never overwritten

Candidates carry a short matched span ('raw') and locator so a curator can find the value in
the paper. They are working files for curation: they contain fragments of source text, so
they are git-ignored and are NOT part of any release.

Usage
  python code/02_extract.py
  python code/02_extract.py --all-screened
  python code/02_extract.py --file tests/fixtures/synthetic_article.xml    # one file, print summary
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from common import CURATED, PROCESSED, ROOT
from extractors import extract_all, extract_table, norm_text

RECORD_COLUMNS = [
    "record_id", "paper_id", "doi", "pmcid", "source_license", "locator", "is_control",
    "polymer", "polymer_class", "polymer_detail",
    "mn_before", "mw_before", "mp_before", "disp_before", "mass_unit_before",
    "mn_after", "mw_after", "mp_after", "disp_after", "mass_unit_after",
    "sec_calibration", "sec_detector", "sec_eluent", "sec_temperature_c",
    "catalyst", "catalyst_loading", "catalyst_loading_unit", "cocatalyst_additives",
    "light_source", "wavelength_nm", "wavelength_range_nm", "light_color", "irradiance", "irradiance_unit",
    "solvent", "concentration", "concentration_unit", "atmosphere", "temperature_c",
    "time", "time_unit",
    "products", "product_yields", "yield_basis", "yield_uncertainty", "replicates",
    "extraction_method", "extractor", "source_verified", "blind_verified", "qa_flags",
    "notes", "curator", "curation_date",
]


def _txt(el) -> str:
    return norm_text("".join(el.itertext())).strip() if el is not None else ""


def _strip_ns(root):
    for el in root.iter():
        if isinstance(el.tag, str) and "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]
    return root


def parse_jats(path: Path):
    """Yield (locator, kind, payload). kind is 'text' (payload=str) or 'table' (payload=(header, rows))."""
    root = _strip_ns(ET.parse(path).getroot())
    art_title = _txt(root.find(".//article-meta/title-group/article-title"))
    if art_title:
        yield "title", "text", art_title
    ab = root.find(".//article-meta/abstract")
    if ab is not None:
        yield "abstract", "text", _txt(ab)

    def walk(sec, trail):
        title = _txt(sec.find("title")) if sec.find("title") is not None else ""
        here = trail + [title] if title else trail
        p_i = 0
        for child in sec:
            if child.tag == "p":
                p_i += 1
                nested = [el for el in child.iter() if el.tag in ("table-wrap", "fig") and el is not child]
                if nested:
                    # Tables/figures embedded in a paragraph: emit them as their own blocks and keep the
                    # paragraph text without their cells (otherwise cells run together, e.g. '67,00053,000').
                    import copy
                    para = copy.deepcopy(child)
                    for el in list(para.iter()):
                        for sub in list(el):
                            if sub.tag in ("table-wrap", "fig"):
                                tail = sub.tail
                                el.remove(sub)
                                if tail:
                                    el.text = (el.text or "") + " " + tail
                    yield f"{' > '.join(here) or 'body'} ¶{p_i}", "text", _txt(para)
                    for el in nested:
                        if el.tag == "table-wrap":
                            yield from table(el)
                        else:
                            yield f"{_txt(el.find('label')) or 'Figure'} caption", "text", _txt(el.find("caption"))
                else:
                    yield f"{' > '.join(here) or 'body'} ¶{p_i}", "text", _txt(child)
            elif child.tag == "sec":
                yield from walk(child, here)
            elif child.tag == "fig":
                lab = _txt(child.find("label")) or "Figure"
                yield f"{lab} caption", "text", _txt(child.find("caption"))
            elif child.tag == "table-wrap":
                yield from table(child)
            elif child.tag in ("list", "disp-quote", "boxed-text"):
                yield f"{' > '.join(here) or 'body'} list", "text", _txt(child)

    def table(tw):
        lab = _txt(tw.find("label")) or "Table"
        cap = _txt(tw.find("caption"))
        if cap:
            yield f"{lab} caption", "text", cap
        tbl = tw.find(".//table")
        if tbl is not None:
            header, rows = [], []
            thead = tbl.find("thead")
            if thead is not None:
                hrows = thead.findall("tr")
                if hrows:
                    # merge multi-row headers column-wise, expanding colspan/rowspan so that a spanning
                    # cell such as 'Mn (g/mol)' over 'Before | After' labels both columns
                    grid = {}
                    for ri, r in enumerate(hrows):
                        ci = 0
                        for c in r.findall("./*"):
                            while (ri, ci) in grid:
                                ci += 1
                            cs = int(c.get("colspan", 1) or 1)
                            rs = int(c.get("rowspan", 1) or 1)
                            for dr in range(rs):
                                for dc in range(cs):
                                    grid[(ri + dr, ci + dc)] = _txt(c)
                            ci += cs
                    width = max(k[1] for k in grid) + 1
                    header = []
                    for ci in range(width):
                        parts = []
                        for ri in range(len(hrows)):
                            t = grid.get((ri, ci), "")
                            if t and (not parts or parts[-1] != t):
                                parts.append(t)
                        header.append(" ".join(parts).strip())
            body_rows = tbl.findall("tbody/tr") or [r for r in tbl.findall(".//tr") if thead is None or r not in thead.findall("tr")]
            for r in body_rows:
                rows.append([_txt(c) for c in r.findall("./*")])
            if not header and rows:
                header, rows = rows[0], rows[1:]
            yield lab, "table", (header, rows)
        for fn in tw.findall(".//table-wrap-foot"):
            yield f"{lab} footnote", "text", _txt(fn)

    body = root.find(".//body")
    if body is not None:
        yield from walk(body, [])
    back = root.find(".//back")
    if back is not None:
        for tw in back.iter("table-wrap"):
            yield from table(tw)
        for sm in back.iter("supplementary-material"):
            cap = _txt(sm.find("caption"))
            if cap:
                yield "supplementary caption", "text", cap
    # floats-group (common in PMC) holds figures and tables outside body
    fg = root.find(".//floats-group")
    if fg is not None:
        for child in fg:
            if child.tag == "table-wrap":
                yield from table(child)
            elif child.tag == "fig":
                yield f"{_txt(child.find('label')) or 'Figure'} caption", "text", _txt(child.find("caption"))


def extract_file(path: Path, paper_id: str):
    cands = []
    for locator, kind, payload in parse_jats(path):
        if kind == "text":
            if not payload:
                continue
            for c in extract_all(payload):
                cands.append({"paper_id": paper_id, "locator": locator, "source": "text", **c})
        else:
            header, rows = payload
            tc, cols = extract_table(header, rows)
            for c in tc:
                cands.append({"paper_id": paper_id, "locator": f"{locator} r{c.pop('row') + 1} c{c.pop('col') + 1}",
                              "source": "table", **c})
            if cols:
                cands.append({"paper_id": paper_id, "locator": locator, "source": "table",
                              "field": "table_columns_recognised",
                              "value": "; ".join(f"c{i + 1}={f}{'(' + u + ')' if u else ''}" for i, (f, u) in sorted(cols.items())),
                              "unit": "", "raw": " | ".join(header)})
    return cands


def digest(cands):
    """Per-paper summary: counts per field and the most frequent values, for the review sheet."""
    by = collections.defaultdict(list)
    for c in cands:
        by[c["field"]].append(c)
    out = {}
    for field, items in by.items():
        vals = collections.Counter(f"{c['value']}{(' ' + c['unit']) if c.get('unit') else ''}" for c in items)
        out[field] = "; ".join(f"{v} (x{n})" if n > 1 else v for v, n in vals.most_common(6))
    return out


DIGEST_FIELDS = ["polymer", "Mn", "Mw", "Mp", "dispersity", "sec_calibration", "sec_eluent", "catalyst",
                 "wavelength_nm", "wavelength_range_nm", "light_color", "light_source", "irradiance_or_power",
                 "solvent", "time", "temperature", "atmosphere", "product", "yield_or_conversion",
                 "table_columns_recognised"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--all-screened", action="store_true", help="use every auto-passed paper, ignoring include decisions")
    ap.add_argument("--file", help="extract one JATS file and print a summary (no outputs written)")
    a = ap.parse_args()

    if a.file:
        c = extract_file(Path(a.file), Path(a.file).stem)
        for field, val in digest(c).items():
            print(f"{field:28s} {val}")
        print(f"\n{len(c)} candidates")
        return

    scr = CURATED / "screening.csv"
    if not scr.exists():
        sys.exit("data/curated/screening.csv not found; run code/01_fetch.py first")
    with open(scr, encoding="utf-8") as f:
        papers = list(csv.DictReader(f))
    if not a.all_screened:
        papers = [p for p in papers if p.get("include", "").strip().lower() in ("y", "yes", "1", "true")]
        if not papers:
            sys.exit("no papers marked include=y in data/curated/screening.csv (use --all-screened to preview)")

    PROCESSED.mkdir(parents=True, exist_ok=True)
    n_c, n_files, missing = 0, 0, []
    with open(PROCESSED / "candidates.jsonl", "w", encoding="utf-8") as fo, \
         open(PROCESSED / "review_sheet.csv", "w", newline="", encoding="utf-8") as fr:
        w = csv.DictWriter(fr, fieldnames=["paper_id", "doi", "pmcid", "license", "title", "n_candidates"] + DIGEST_FIELDS)
        w.writeheader()
        for p in papers:
            ft = p.get("fulltext", "")
            path = ROOT / ft if ft and not ft.startswith("unavailable") else None
            if not path or not path.exists():
                missing.append(p["paper_id"])
                w.writerow({k: p.get(k, "") for k in ["paper_id", "doi", "pmcid", "license", "title"]} | {"n_candidates": "no full text"})
                continue
            cands = extract_file(path, p["paper_id"])
            n_files += 1
            n_c += len(cands)
            for c in cands:
                fo.write(json.dumps(c, ensure_ascii=False) + "\n")
            w.writerow({k: p.get(k, "") for k in ["paper_id", "doi", "pmcid", "license", "title"]}
                       | {"n_candidates": len(cands)} | {f: digest(cands).get(f, "") for f in DIGEST_FIELDS})

    rec = CURATED / "records.csv"
    if not rec.exists():
        with open(rec, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(RECORD_COLUMNS)
    print(f"{n_files} papers extracted, {n_c} candidates; {len(missing)} without OA full text "
          f"(curate from oa_url in data/processed/corpus.csv if wanted)")


if __name__ == "__main__":
    main()
