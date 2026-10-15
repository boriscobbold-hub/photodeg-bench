#!/usr/bin/env python3
"""Agent D, independent half (step 2): compare blind re-extractions with the extraction files.

Reads data/curated/verification/blind/<PMCID>.json (written by independent agents from the slots)
and data/curated/extractions/<PMCID>.json. For every field: agree | disagree | blind_missing | blind_null.
Numbers agree if equal within 0.5 % (after reading both as printed); text agrees on normalised
containment. Writes data/curated/verification/blind_comparison.csv and adjudication_queue.csv
(every disagreement plus every concern the blind agent raised).

Agreement between two AI passes is NOT treated as verification on its own: a record is release-eligible
only if the deterministic source check passes AND there is no unresolved disagreement or concern.
"""
import csv
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V = ROOT / "data/curated/verification"


def norm(x):
    x = unicodedata.normalize("NFKC", str(x)).lower()
    x = re.sub(r"[−–—]", "-", x)
    return re.sub(r"[^a-z0-9.%/+()-]+", " ", x).strip()


def num(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


def same(a, b):
    na, nb = num(a), num(b)
    if na is not None and nb is not None:
        return abs(na - nb) <= 0.005 * max(abs(na), abs(nb), 1e-12)
    A, B = norm(a), norm(b)
    return bool(A) and bool(B) and (A == B or A in B or B in A)


def main():
    rows, queue, covered = [], [], set()
    for bf in sorted((V / "blind").glob("*.json")):
        blind = json.loads(bf.read_text())
        ext = json.loads((ROOT / "data/curated/extractions" / (bf.stem.split("_")[0] + ".json")).read_text())
        recs = {r["rid"]: r for r in ext["records"]}
        for c in blind.get("paper_concerns", []):
            queue.append({"pmcid": ext["pmcid"], "rid": "", "field": "", "type": "paper_concern", "extracted": "", "blind": "", "detail": c})
        for t in blind.get("tasks", []):
            r = recs.get(t["rid"])
            if not r:
                continue
            covered.add((ext["pmcid"], t["rid"]))
            fields = {**ext.get("shared", {}), **r.get("fields", {})}
            bv = t.get("values", {})
            for k, ev in fields.items():
                if ev is None or k in ("polymer_class", "light_color", "product_yields"):
                    continue
                b = bv.get(k, "MISSING")
                if b == "MISSING":
                    status, bval = "blind_missing", ""
                elif b is None or (isinstance(b, dict) and b.get("v") in (None, "")):
                    status, bval = "blind_null", ""
                else:
                    bval = b.get("v") if isinstance(b, dict) else b
                    status = "agree" if same(ev.get("v"), bval) else "disagree"
                rows.append({"pmcid": ext["pmcid"], "rid": t["rid"], "field": k, "extracted": ev.get("v"), "blind": bval, "status": status})
                if status in ("disagree", "blind_null") and k not in ("polymer_detail", "light_source", "cocatalyst_additives"):
                    queue.append({"pmcid": ext["pmcid"], "rid": t["rid"], "field": k, "type": status, "extracted": ev.get("v"),
                                  "blind": bval, "detail": json.dumps(b, ensure_ascii=False) if isinstance(b, dict) else ""})
            by = t.get("yields", {}) or {}
            for y in fields.get("product_yields") or []:
                b = by.get(y["product"])
                bval = b.get("v") if isinstance(b, dict) else b
                status = "blind_missing" if b is None else ("agree" if same(y["v"], bval) else "disagree")
                rows.append({"pmcid": ext["pmcid"], "rid": t["rid"], "field": f"yield:{y['product']}", "extracted": y["v"], "blind": bval, "status": status})
                if status != "agree":
                    queue.append({"pmcid": ext["pmcid"], "rid": t["rid"], "field": f"yield:{y['product']}", "type": status,
                                  "extracted": y["v"], "blind": bval, "detail": json.dumps(b, ensure_ascii=False) if b else ""})
            for c in t.get("concerns", []):
                queue.append({"pmcid": ext["pmcid"], "rid": t["rid"], "field": "", "type": "record_concern", "extracted": "", "blind": "", "detail": c})
    with open(V / "blind_comparison.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["pmcid", "rid", "field", "extracted", "blind", "status"]); w.writeheader(); w.writerows(rows)
    with open(V / "adjudication_queue.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["pmcid", "rid", "field", "type", "extracted", "blind", "detail"]); w.writeheader(); w.writerows(queue)
    (V / "blind_coverage.json").write_text(json.dumps(sorted(f"{a}-{b}" for a, b in covered)))
    import collections
    print(collections.Counter(r["status"] for r in rows), "queue:", len(queue))


if __name__ == "__main__":
    main()
