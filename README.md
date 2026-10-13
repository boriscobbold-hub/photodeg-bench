> **Status: DRAFT, pre-release, handed to curator.** v1.0.0 not yet released. Corpus fetched 2026-10-12 (691 open-access papers, 267 with full text, 154 of those on topic); 0 records curated; harmonization rules unset. See [docs/HANDOFF.md](docs/HANDOFF.md). DOI: [DOI: added after the Zenodo deposit].

# PhotoDeg-Bench

An open, harmonized benchmark of **visible-light polymer deconstruction**: what polymer went in, how big it was before and after (and how that was measured), what catalyst and light did it, in what solvent, for how long, and what came out.

## Why

Photochemical routes to break down plastics are reported in incompatible ways. One paper gives M<sub>n</sub> from SEC against polystyrene standards, the next gives M<sub>w</sub> from light scattering, a third gives only a product yield; light is "blue LEDs" in one and "456 nm, 40 W" in another. Without a common basis it is hard to say which route actually deconstructs more polymer per hour of light, and that gap slows the scale-up choices that upcycling programs, including DOE-funded ones, have to make. PhotoDeg-Bench records each experiment as reported, then applies published, versioned harmonization rules so records can be compared on a stated basis, with a comparability tier telling users how far to trust each comparison.

## What is in a record

One record = one polymer sample × one condition set × one reported timepoint in one source paper. Fields: polymer and class; M<sub>n</sub>/M<sub>w</sub>/M<sub>p</sub>/Đ before and after as reported; SEC calibration, detector, eluent and temperature; catalyst and loading; light source, wavelength or band, irradiance; solvent, concentration, atmosphere, temperature; time; products with yields and their basis; the source DOI, license and a locator (table/figure/section) pointing at the value. Harmonized columns (suffix `_h`, plus `retained_fraction`, `scissions_per_chain`, `wavelength_band`, `time_h`, `tier`) are computed by `code/04_harmonize.py` from `rules/harmonization.yaml`. Every column is defined in [docs/CODEBOOK.md](docs/CODEBOOK.md).

## Who decides what

The harmonization rules are written by the curator from SEC practice, and every record is entered or confirmed by the curator against its source (`checked_against_source = y` is enforced). Code proposes candidate values from open-access full text and executes the rules; it does not choose rules or write release records. See [docs/CURATION_GUIDE.md](docs/CURATION_GUIDE.md).

## How to run

Python 3.10+.

```bash
pip install -r requirements.txt
export PHOTODEG_EMAIL=you@example.org     # polite-pool contact for OpenAlex and Europe PMC

python code/01_fetch.py          # corpus from Europe PMC + OpenAlex, OA JATS full text, PROVENANCE.txt
#  -> curator screens papers in data/curated/screening.csv (include = y/n, reason)
python code/02_extract.py --all-screened   # candidate values for every screened paper (before screening)
python code/02b_triage.py        # rank papers: on-topic first, then evidence score (screening aid only)
python code/02_extract.py        # after screening: candidates + review sheet for included papers only
#  -> curator enters records in data/curated/records.csv, sets rules/harmonization.yaml
python code/03_validate.py       # schema, range and provenance checks; must pass with 0 errors
python code/04_harmonize.py      # benchmark table; refuses while any rule is unset
python code/05_qa.py             # QA report + paper/stats.json
python code/06_figures.py        # figures (DRAFT-stamped until --final)

python -m unittest discover -s tests -v   # tests run on synthetic fixtures only
```

`make all` runs validate → harmonize → QA → figures once curation is done.

## Outputs

| File | What |
|---|---|
| `data/processed/photodeg_bench_v1.0.csv` | the benchmark table |
| `data/processed/qa_report.txt` | flow counts, completeness, ranges, named spot checks |
| `data/processed/harmonization_log.csv` | every record a rule excluded or transformed |
| `data/raw/PROVENANCE.txt` | every fetched file: date, bytes, SHA-256, URL, query |
| `rules/harmonization.yaml` | the rules, with the curator's rationale |
| `paper/stats.json`, `paper/figures/` | numbers and figures for any write-up |

## Sources

- Europe PMC REST API (search and `fullTextXML`, open-access subset), https://europepmc.org/RestfulWebService. Metadata CC0; each article under its own license, recorded per record.
- OpenAlex works API, https://api.openalex.org. Metadata CC0.

Search strings are in `config/search.yaml`; fetch dates and hashes in `data/raw/PROVENANCE.txt`. Full-text XML is not redistributed (licenses vary); re-fetch with `01_fetch.py`.

## Limitations

See [docs/LIMITATIONS.md](docs/LIMITATIONS.md). In short: open-access literature only, SEC values from mismatched standards are not absolute masses, and many papers under-report light dose.

## License and citation

Code MIT; data and documentation CC BY 4.0 (see `LICENSE`). Cite via `CITATION.cff` or the Zenodo DOI once minted.

## Contributing records

Corrections and new records are welcome as GitHub issues with the source DOI and locator.

## Maintainer

[VERIFY: name, ORCID, contact as in AUTHORS.json]
