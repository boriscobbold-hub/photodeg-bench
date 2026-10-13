#!/usr/bin/env python3
"""Fill the author block everywhere it is needed (AUTHORS.json, CITATION.cff, LICENSE copyright,
docs/zenodo_metadata.json) from the author's own details. Nothing is guessed: every argument is required.

  python tools/set_authors.py --given Boris --family Surname --orcid 0000-0000-0000-0000 \
      --email you@example.org --affiliation "Independent Researcher, City, State, USA" \
      --roles "Conceptualization;Supervision" --repo-url https://github.com/<user>/photodeg-bench
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    for a in ("given", "family", "orcid", "email", "affiliation", "roles", "repo-url"):
        ap.add_argument(f"--{a}", required=True)
    a = ap.parse_args()
    if not re.fullmatch(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]", a.orcid):
        raise SystemExit("ORCID must look like 0000-0000-0000-0000")
    name = f"{a.given} {a.family}"
    p = ROOT / "AUTHORS.json"
    d = json.loads(p.read_text())
    d["_comment"] = "Author block; README, CITATION.cff, Zenodo creators and LICENSE read from here."
    d["authors"] = [{"name": name, "family": a.family, "given": a.given, "orcid": a.orcid, "email": a.email,
                     "affiliation": a.affiliation, "roles": [r.strip() for r in a.roles.split(";") if r.strip()], "corresponding": True}]
    p.write_text(json.dumps(d, indent=1, ensure_ascii=False))
    c = (ROOT / "CITATION.cff").read_text()
    c = c.replace('[VERIFY: family name]', a.family).replace('[VERIFY: given name]', a.given)
    c = c.replace('[VERIFY: 0000-0000-0000-0000]', a.orcid).replace('[VERIFY: https://github.com/<user>/photodeg-bench]', a.repo_url)
    c = "\n".join(l for l in c.splitlines() if not l.startswith("doi:")) + "\n"   # added back once Zenodo mints the DOI
    (ROOT / "CITATION.cff").write_text(c)
    lic = (ROOT / "LICENSE").read_text().replace("[VERIFY: copyright holder name as in AUTHORS.json]", name)
    (ROOT / "LICENSE").write_text(lic)
    z = ROOT / "docs/zenodo_metadata.json"
    m = json.loads(z.read_text())
    m.pop("_comment", None)
    m["creators"] = [{"name": f"{a.family}, {a.given}", "orcid": a.orcid, "affiliation": a.affiliation}]
    m["related_identifiers"] = [{"identifier": a.repo_url, "relation": "isSupplementTo", "scheme": "url"}]
    z.write_text(json.dumps(m, indent=1, ensure_ascii=False))
    print(f"author block set for {name}; CITATION.cff has no doi line until the Zenodo deposit returns one")


if __name__ == "__main__":
    main()
