#!/usr/bin/env python3
"""Render docs/templates/*.md -> their targets, filling {{key}} and {{a.b}} from paper/stats.json.

Every number quoted in README, methods, harmonization report and limitations comes from the stats file,
so text cannot drift from data. Unknown keys fail loudly.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = {"README.md.tmpl": "README.md", "METHODS_AUTOMATED_CURATION.md.tmpl": "docs/METHODS_AUTOMATED_CURATION.md",
           "HARMONIZATION_REPORT.md.tmpl": "docs/HARMONIZATION_REPORT.md", "LIMITATIONS.md.tmpl": "docs/LIMITATIONS.md",
           "MANUSCRIPT_OUTLINE.md.tmpl": "docs/MANUSCRIPT_OUTLINE.md"}


def get(stats, key):
    cur = stats
    for part in key.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            raise KeyError(key)
    if isinstance(cur, float):
        return f"{cur:.3g}"
    if isinstance(cur, dict):
        return ", ".join(f"{k} {v}" for k, v in cur.items())
    return str(cur)


def main():
    stats = json.loads((ROOT / "paper/stats.json").read_text())
    stats["pct_lost_to_access"] = round(100 * stats["share_in_scope_lost_to_access"])
    bad = []
    for t, target in TARGETS.items():
        src = ROOT / "docs/templates" / t
        if not src.exists():
            continue
        def sub(m):
            try:
                return get(stats, m.group(1))
            except KeyError:
                bad.append(f"{t}: {m.group(1)}")
                return m.group(0)
        (ROOT / target).write_text(re.sub(r"\{\{\s*([\w.]+)\s*\}\}", sub, src.read_text()))
    if bad:
        sys.exit("unknown stats keys: " + "; ".join(bad))
    print("docs rendered:", ", ".join(TARGETS.values()))


if __name__ == "__main__":
    main()
