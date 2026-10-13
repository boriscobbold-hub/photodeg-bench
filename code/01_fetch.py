#!/usr/bin/env python3
"""Step 1: build the candidate corpus from Europe PMC and OpenAlex, then fetch OA full text.

Outputs
  data/raw/europepmc/search_q{i}_p{n}.json   raw search pages
  data/raw/openalex/search_s{i}_p{n}.json    raw search pages
  data/raw/fulltext/{PMCID}.xml              JATS full text (Europe PMC OA subset)
  data/raw/PROVENANCE.txt                    one line per file: date, bytes, sha256, URL
  data/processed/corpus.csv                  one row per unique paper, merged + screened

Usage
  PHOTODEG_EMAIL=you@example.org python code/01_fetch.py            # full run
  python code/01_fetch.py --skip-fulltext                           # metadata only
  python code/01_fetch.py --max-pages 1                             # quick smoke test
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import urllib.error

from common import (CURATED, PROCESSED, PROVENANCE, RAW, ROOT, contact_email, http_get,
                    load_yaml, log_provenance, norm_doi, write_json)

EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"
OPENALEX = "https://api.openalex.org/works"


def fetch_europepmc(cfg, email, max_pages):
    out = {}
    for qi, q in enumerate(cfg["europepmc"]["queries"]):
        cursor, page = "*", 0
        while True:
            params = {"query": q, "format": "json", "resultType": "core",
                      "pageSize": cfg["europepmc"].get("page_size", 1000), "cursorMark": cursor}
            if email:
                params["email"] = email
            data = http_get(f"{EPMC}/search", params, email)
            path = RAW / "europepmc" / f"search_q{qi}_p{page}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            log_provenance(path, f"{EPMC}/search", note=f"query[{qi}]={q} cursorMark={cursor}")
            d = json.loads(data)
            results = d.get("resultList", {}).get("result", [])
            for r in results:
                key = norm_doi(r.get("doi")) or (r.get("pmcid") or r.get("id"))
                out.setdefault(key, {"epmc": r, "queries": set()})["queries"].add(f"epmc{qi}")
            print(f"europepmc q{qi} p{page}: {len(results)} results (hitCount {d.get('hitCount')})")
            nxt = d.get("nextCursorMark")
            page += 1
            if not results or not nxt or nxt == cursor or (max_pages and page >= max_pages):
                break
            cursor = nxt
    return out


def fetch_openalex(cfg, email, max_pages):
    out = {}
    oa = cfg["openalex"]
    year_min, year_max = cfg.get("year_min"), cfg.get("year_max")
    flt = oa["filter"]
    if year_min:
        flt += f",from_publication_date:{year_min}-01-01"
    if year_max:
        flt += f",to_publication_date:{year_max}-12-31"
    for si, s in enumerate(oa["searches"]):
        cursor, page = "*", 0
        while True:
            params = {"filter": f"{flt},title_and_abstract.search:{s}", "per_page": oa.get("per_page", 200), "cursor": cursor}
            if email:
                params["mailto"] = email
            data = http_get(OPENALEX, params, email)
            path = RAW / "openalex" / f"search_s{si}_p{page}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            log_provenance(path, OPENALEX, note=f"search[{si}]={s} filter={flt} cursor={cursor}")
            d = json.loads(data)
            results = d.get("results", [])
            for w in results:
                key = norm_doi(w.get("doi")) or w.get("id")
                out.setdefault(key, {"oa": w, "queries": set()})["queries"].add(f"oa{si}")
            print(f"openalex s{si} p{page}: {len(results)} results (count {d.get('meta', {}).get('count')})")
            nxt = d.get("meta", {}).get("next_cursor")
            page += 1
            cap = max_pages or oa.get("max_pages") or 0
            if not results or not nxt or (cap and page >= cap):
                if cap and page >= cap and nxt:
                    print(f"  WARNING openalex s{si}: stopped at page cap {cap}; results truncated")
                break
            cursor = nxt
    return out


def abstract_from_inverted(inv):
    if not inv:
        return ""
    pos = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    return " ".join(pos[i] for i in sorted(pos))


def screen(text, cfg):
    t = text.lower()
    s = cfg["screening"]
    hit = lambda terms: any(term in t for term in terms)  # noqa: E731
    return hit(s["light_terms"]) and hit(s["polymer_terms"]) and hit(s["outcome_terms"])


def merge(epmc, oa, cfg):
    rows = {}
    for key, v in epmc.items():
        r = v["epmc"]
        rows[key] = {
            "paper_id": key,
            "doi": norm_doi(r.get("doi")),
            "pmcid": r.get("pmcid", ""),
            "pmid": r.get("pmid", ""),
            "openalex_id": "",
            "title": (r.get("title") or "").strip(),
            "year": r.get("pubYear", ""),
            "journal": ((r.get("journalInfo") or {}).get("journal") or {}).get("title", ""),
            "license": (r.get("license") or "").lower(),
            "oa_status": "epmc_oa" if r.get("isOpenAccess") == "Y" else "",
            "oa_url": "",
            "abstract": re.sub(r"<[^>]+>", "", r.get("abstractText") or ""),
            "found_by": ";".join(sorted(v["queries"])),
        }
    for key, v in oa.items():
        w = v["oa"]
        loc = w.get("best_oa_location") or w.get("primary_location") or {}
        pmcid = ((w.get("ids") or {}).get("pmcid") or "").rsplit("/", 1)[-1]
        if pmcid and not pmcid.upper().startswith("PMC"):
            pmcid = "PMC" + pmcid
        row = rows.setdefault(key, {
            "paper_id": key, "doi": norm_doi(w.get("doi")), "pmcid": pmcid, "pmid": "",
            "openalex_id": "", "title": (w.get("title") or "").strip(),
            "year": w.get("publication_year", ""),
            "journal": ((loc.get("source") or {}).get("display_name") or ""),
            "license": "", "oa_status": "", "oa_url": "",
            "abstract": abstract_from_inverted(w.get("abstract_inverted_index")), "found_by": ""})
        row["openalex_id"] = w.get("id", "")
        row["pmcid"] = row["pmcid"] or pmcid
        row["license"] = row["license"] or (loc.get("license") or "")
        row["oa_status"] = row["oa_status"] or ((w.get("open_access") or {}).get("oa_status") or "")
        row["oa_url"] = loc.get("pdf_url") or loc.get("landing_page_url") or ""
        row["found_by"] = ";".join(sorted(set(filter(None, row["found_by"].split(";"))) | v["queries"]))
        if not row["abstract"]:
            row["abstract"] = abstract_from_inverted(w.get("abstract_inverted_index"))
    year_min = cfg.get("year_min")
    for row in rows.values():
        row["in_year_scope"] = "y" if (not year_min or (str(row["year"]).isdigit() and int(row["year"]) >= year_min)) else "n"
        row["auto_screen"] = "pass" if screen(f"{row['title']} {row['abstract']}", cfg) else "fail"
    return sorted(rows.values(), key=lambda r: (str(r["year"]), r["paper_id"]))


def fetch_fulltext(rows, email):
    got = 0
    for row in rows:
        if row["auto_screen"] != "pass" or row["in_year_scope"] != "y" or not row["pmcid"]:
            row["fulltext"] = ""
            continue
        path = RAW / "fulltext" / f"{row['pmcid']}.xml"
        if path.exists():
            row["fulltext"] = str(path.relative_to(ROOT))
            got += 1
            continue
        url = f"{EPMC}/{row['pmcid']}/fullTextXML"
        try:
            data = http_get(url, email=email)
        except urllib.error.HTTPError as e:
            row["fulltext"] = f"unavailable:{e.code}"
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        log_provenance(path, url)
        row["fulltext"] = str(path.relative_to(ROOT))
        got += 1
    print(f"full text: {got} JATS files")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--max-pages", type=int, default=0, help="cap pages per query (0 = all)")
    ap.add_argument("--skip-fulltext", action="store_true")
    a = ap.parse_args()

    cfg = load_yaml(ROOT / "config" / "search.yaml")
    email = contact_email(cfg)
    if not email:
        print("note: set PHOTODEG_EMAIL so OpenAlex and Europe PMC can contact you; continuing.", file=sys.stderr)

    with open(PROVENANCE, "a", encoding="utf-8") as f:
        f.write("# run started; search config recorded on the next line\n")
    log_provenance(ROOT / "config" / "search.yaml", "config/search.yaml", note="search strategy used for this run")

    epmc = fetch_europepmc(cfg, email, a.max_pages)
    oa = fetch_openalex(cfg, email, a.max_pages)
    rows = merge(epmc, oa, cfg)
    if not a.skip_fulltext:
        fetch_fulltext(rows, email)
    else:
        for r in rows:
            r["fulltext"] = ""

    PROCESSED.mkdir(parents=True, exist_ok=True)
    cols = ["paper_id", "doi", "pmcid", "pmid", "openalex_id", "title", "year", "journal", "license",
            "oa_status", "oa_url", "found_by", "in_year_scope", "auto_screen", "fulltext"]
    with open(PROCESSED / "corpus.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    # Screening sheet for Boris: one row per auto-passed paper; decisions are his.
    scr = CURATED / "screening.csv"
    existing = {}
    if scr.exists():
        with open(scr, encoding="utf-8") as f:
            existing = {r["paper_id"]: r for r in csv.DictReader(f)}
    with open(scr, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["paper_id", "doi", "pmcid", "year", "title", "license",
                                          "fulltext", "include", "exclusion_reason", "reviewer", "review_date"])
        w.writeheader()
        for r in rows:
            if r["auto_screen"] != "pass" or r["in_year_scope"] != "y":
                continue
            prev = existing.get(r["paper_id"], {})
            w.writerow({k: r.get(k, "") for k in ["paper_id", "doi", "pmcid", "year", "title", "license", "fulltext"]}
                       | {k: prev.get(k, "") for k in ["include", "exclusion_reason", "reviewer", "review_date"]})

    n_pass = sum(r["auto_screen"] == "pass" and r["in_year_scope"] == "y" for r in rows)
    write_json(PROCESSED / "fetch_stats.json", {
        "n_unique_papers": len(rows),
        "n_europepmc": len(epmc), "n_openalex": len(oa),
        "n_auto_screen_pass": n_pass,
        "n_fulltext": sum(bool(r.get("fulltext")) and not r["fulltext"].startswith("unavailable") for r in rows),
    })
    print(f"corpus: {len(rows)} unique papers, {n_pass} pass auto-screen -> data/curated/screening.csv")


if __name__ == "__main__":
    main()
