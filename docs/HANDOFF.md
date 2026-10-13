# Handoff at end of build session (2026-10-12)

> DRAFT. Where PhotoDeg-Bench stands and what remains, all of it the curator's work.

## Done
- Pipeline: fetch → extract → triage → validate → harmonize → QA → figures, with 18 tests on synthetic fixtures (all passing).
- **Corpus fetched 2026-10-12.** Europe PMC 277 + OpenAlex 445 → 691 unique open-access papers; 602 pass the automatic screen and year floor (2010+); 267 have Europe PMC full-text XML (35 MB, git-ignored, hashes in `data/raw/PROVENANCE.txt`).
- **Candidates extracted** from all 267 full texts (52,061 candidate values with locators; git-ignored working file).
- **Triage:** 154 full-text papers on topic by title/abstract; licenses among them: 120 CC BY, 19 CC BY-NC-ND, 13 CC BY-NC, 2 unknown. 26 score ≥ 4.

## Not done, and why
v1.0 has **no records** and is **not released**. By design, records and rules come only from the curator: the code proposes candidates and executes rules, it never writes a release record or picks a rule. Nothing was pushed to GitHub or deposited on Zenodo; the publish gate blocks while draft stamps and `[VERIFY]` fields remain.

## To release v1.0 (curator)
1. Fill `AUTHORS.json`; confirm licenses (code MIT, data CC BY 4.0) and the polymer scope.
2. Screen from `data/processed/triage.csv` into `data/curated/screening.csv` (include y/n + reason). 335 auto-passed papers have no Europe PMC full text; decide whether to curate any from their `oa_url`.
3. `python code/02_extract.py` for included papers → enter records in `data/curated/records.csv`, each checked against the source.
4. Set all 14 rules in `rules/harmonization.yaml` with rationale.
5. `make all`, work the QA spot checks, complete `docs/VERIFY_CHECKLIST.md`.
6. `python code/06_figures.py --final`, remove banners, `python tools/publish_gate.py .` → follow `docs/PUBLISH_GUIDE.md` (GitHub, then Zenodo sandbox, then Zenodo).
7. Log the DOI in `docs/evidence_log.csv` the same day.
