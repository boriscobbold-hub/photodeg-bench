#!/usr/bin/env python3
"""Confirm each included article's license from Crossref (version-of-record license URL) and compare
with the license recorded from Europe PMC/OpenAlex metadata. Writes data/curated/license_check.csv.
A mismatch or a missing Crossref license is reported, not silently resolved."""
import csv
import datetime as dt
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def crossref(doi):
    req = urllib.request.Request(f"https://api.crossref.org/works/{doi}", headers={"User-Agent": "PhotoDeg-Bench license check"})
    with urllib.request.urlopen(req, timeout=30) as r:
        m = json.loads(r.read())["message"]
    vor = [l["URL"] for l in m.get("license", []) if l.get("content-version") in ("vor", "unspecified")]
    return vor[0] if vor else ""


def norm(url):
    u = url.lower().rstrip("/")
    for k in ("by-nc-nd", "by-nc-sa", "by-nc", "by-sa", "by", "zero"):
        if f"/licenses/{k}/" in u + "/" or (k == "zero" and "publicdomain/zero" in u):
            return "cc0" if k == "zero" else f"cc-{k}"
    return u


def main():
    rows = []
    for f in sorted((ROOT / "data/curated/extractions").glob("*.json")):
        d = json.loads(f.read_text())
        if d["screen"]["decision"] != "include":
            continue
        recorded = d["source_license"].lower().replace(" ", "-")
        try:
            url = crossref(d["doi"])
        except Exception as e:  # noqa: BLE001
            url = f"error: {e}"
        cr = norm(url) if url and not url.startswith("error") else ""
        rows.append({"pmcid": d["pmcid"], "doi": d["doi"], "recorded_license": recorded, "crossref_license_url": url,
                     "crossref_license": cr, "agrees": "y" if cr == recorded else ("unknown" if not cr else "n"),
                     "checked": dt.date.today().isoformat()})
    with open(ROOT / "data/curated/license_check.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    for r in rows:
        print(r["pmcid"], r["recorded_license"], "|", r["crossref_license_url"], "|", r["agrees"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
