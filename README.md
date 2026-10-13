> **Status: v1.0.0 release candidate, not yet published.** Scientific readiness is machine-checked (see [docs/RELEASE_READINESS.md](docs/RELEASE_READINESS.md)); public release awaits the author's authorization. DOI: assigned at deposit.

# PhotoDeg-Bench

An open, harmonized benchmark of **visible-light photochemical polymer deconstruction**: which polymer, how its molar mass changed (and how that was measured), which catalyst and light, in what solvent, for how long, and what it turned into.

**v1.0 in numbers:** 87 verified records (29 with molar mass before and after, 75 with product yields, 20 controls) from 10 open-access papers, selected from 691 papers found in Europe PMC and OpenAlex.

## Why

Photochemical routes to break down plastics are reported in incompatible ways. One paper gives M<sub>n</sub> from SEC against polystyrene standards, the next gives M<sub>w</sub> with no calibration stated, a third gives only a benzoic acid yield; light is "blue LEDs" in one and "456 nm, 40 W" in another. PhotoDeg-Bench records each experiment as reported, with a pointer to where each value sits in the source, then applies published harmonization rules and labels how comparable each record is. The aim is a common yardstick for comparing routes, including for upcycling programs deciding what to scale.

## How v1.0 was curated: read this first

**v1.0 was curated by an AI system (Claude), not by a human expert reading each paper.** The author delegated screening, extraction and harmonization decisions to an automated, auditable workflow:

1. **Screening.** All 602 candidate papers were screened against written eligibility criteria ([docs/ELIGIBILITY.md](docs/ELIGIBILITY.md)), with a code and rationale for each ([data/curated/screening_log.csv](data/curated/screening_log.csv)).
2. **Extraction.** Every value is recorded with its locator (table cell, paragraph, caption) and the literal source string it was read from ([docs/EXTRACTION_PROTOCOL.md](docs/EXTRACTION_PROTOCOL.md)).
3. **Deterministic verification.** A script re-parses each article and checks that every source string occurs at its locator and that the number matches: 1800 fields, results matched 1411, inferred 389.
4. **Independent blind re-extraction.** Separate agents, without seeing the first extraction, re-read every article for every record. Disagreements (agree 1248, disagree 183, blind_null 99, blind_missing 36) were adjudicated against the source text and logged (43 adjudications, 0 unresolved). Agreement between two AI passes is never treated as verification on its own.
5. **Harmonization.** Fifteen documented rules ([rules/harmonization.yaml](rules/harmonization.yaml), [docs/HARMONIZATION_REPORT.md](docs/HARMONIZATION_REPORT.md)); two scope/legal rules are escalated to the author.

Details, including what this method can and cannot guarantee: [docs/METHODS_AUTOMATED_CURATION.md](docs/METHODS_AUTOMATED_CURATION.md).

## What is in a record

One record = one polymer sample × one condition set × one reported time point in one paper. As-reported fields (polymer, M<sub>n</sub>/M<sub>w</sub>/M<sub>p</sub>/Đ before and after, SEC calibration/detector/eluent, catalyst and loading, light source/wavelength/colour/power, solvent, concentration, atmosphere, temperature, time, products and yields with their basis) plus harmonized fields (molar masses in kg/mol, retained fraction, wavelength band, thermal regime, time in hours, comparability tiers) and QA flags. Every column: [docs/CODEBOOK.md](docs/CODEBOOK.md). Controlled vocabularies: [docs/VOCABULARIES.md](docs/VOCABULARIES.md).

## Main files

| File | What |
|---|---|
| `data/processed/photodeg_bench_v1.0.csv` | the benchmark table |
| `data/curated/evidence.csv` | every field: value, locator, source string, verification outcome |
| `data/curated/qa_flags.csv` | per-record flags (approximate values, standard conditions applied, heated runs, SEC estimates) |
| `data/curated/extractions/*.json` | extraction files, including observations seen but not recorded and why |
| `data/curated/screening_log.csv` | decision, criterion and rationale for all 602 screened papers |
| `data/curated/verification/` | deterministic results, blind comparison, adjudications |
| `data/processed/qa_report.txt`, `exceptions.csv` | QA report and every exception |
| `paper/stats.json`, `paper/figures/` | every number and figure in the docs |

## Run it

```bash
pip install -r requirements.txt
export PHOTODEG_EMAIL=you@example.org            # polite-pool contact for OpenAlex / Europe PMC
python tools/autonomous_release.py --target v1.0 # resumes from checkpoints; builds the release candidate
python tools/autonomous_release.py --target v1.0 --status
python -m unittest discover -s tests -v
```

Full-text XML is not redistributed; `--refresh` re-fetches it and `data/raw/PROVENANCE.txt` holds each file's SHA-256. AI stages for new papers need `ANTHROPIC_API_KEY` on the runner (`config/llm.yaml`); without it, unprocessed papers are reported and nothing unverified is released.

## Limitations

The largest: 75% of in-scope papers (54) had no full text retrievable by this pipeline, including several central studies, so v1.0 is a verified sample of the open literature, not a census. See [docs/LIMITATIONS.md](docs/LIMITATIONS.md).

## License and citation

Code MIT; data and documentation CC BY 4.0 (see `LICENSE`). Each record carries its source article's license. Cite via `CITATION.cff` or the Zenodo DOI once minted. Authors: see `AUTHORS.json`.
