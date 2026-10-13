# Curation guide

> DRAFT. For the curator. The code proposes; the curator decides.

## 1. Screen papers

Start from `data/processed/triage.csv`, not the raw screening sheet. It lists the 602 auto-passed papers with on-topic full-text papers first (title and abstract mention light, a deconstruction outcome and a synthetic polymer), then by an evidence score (0-6: SEC mass values, a molar-mass table, an SEC calibration statement, a visible wavelength, a named polymer, a named catalyst). The topic flag is a regex, not a judgment: it lets through materials papers that only *use* a polymer (polyester fabric supports, PMMA fibres for dye degradation) and may miss papers that phrase things unusually. Record every decision in `screening.csv`.

In `data/curated/screening.csv` (every row passed the loose automatic screen and the year floor), set for each paper:

- `include`: `y` or `n`
- `exclusion_reason` when `n` (use a short fixed vocabulary so the QA report can count them, e.g. `not visible light`, `small molecule only`, `no polymer outcome`, `review`, `UV only`, `out of scope polymer`)
- `reviewer`, `review_date`

Re-running `01_fetch.py` keeps your decisions for papers already in the sheet.

## 2. Read candidates

`02_extract.py` writes `data/processed/review_sheet.csv` (one line per paper: the most frequent candidate values per field) and `data/processed/candidates.jsonl` (every candidate with its locator, e.g. `Table 1 r3 c6`). Use them to find values fast; never copy a value without looking at it in the paper. Known blind spots: values only in figures (plots), values only in SI PDFs, tables whose header says `Mn × 10⁻³` (flagged as `header scale`), and unit-less numbers in text.

## 3. Enter records

One row per experiment in `data/curated/records.csv` (headers created by `02_extract.py`). Enter values as reported, in the reported unit. Record controls (dark, no catalyst) as their own rows with `control` in `notes`. Set `checked_against_source = y` only after comparing every field with the source.

## 4. Set the rules

Fill `rules/harmonization.yaml`: `status: set`, a `decision`, and a `rationale` in your own words for each rule. `04_harmonize.py` refuses to run until every required rule is set.

## 5. Validate, harmonize, check

`make all`. Fix every validation error. Then work through the spot-check list at the end of `data/processed/qa_report.txt` and tick them off in `docs/VERIFY_CHECKLIST.md`.
