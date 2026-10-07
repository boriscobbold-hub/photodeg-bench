# Verification checklist (curator completes before v1.0.0 release)

> DRAFT. Initial and date each line. `tools/publish_gate.py` checks the mechanical items; these are yours.

## Reproduce
- [ ] `01_fetch.py` run on your machine; fetch date recorded in BUILD_SPEC and PROVENANCE.txt
- [ ] Search strings in `config/search.yaml` reviewed; recall checked against 5 papers you know should be in (list them here)
- [ ] Full pipeline re-run from a clean clone; outputs match the committed versions
- [ ] `python -m unittest discover -s tests` passes

## Rules
- [ ] Every rule in `rules/harmonization.yaml` set, with rationale in your own words
- [ ] If universal calibration is used: each Mark-Houwink pair cited, eluent and temperature match the records it is applied to
- [ ] Tier definitions re-read against three records you know well; each lands in the tier you expect

## Records
- [ ] Every record has `checked_against_source = y`
- [ ] `03_validate.py`: 0 errors; every warning read and either fixed or explained in `notes`
- [ ] QA spot checks done: 5 random (seed in qa_report), 5 lowest and 5 highest retained fraction, every mass increase
- [ ] Five records re-checked by hand a week after entry (fresh eyes)

## Licensing
- [ ] Source-license policy (R14) set; excluded records reviewed in `harmonization_log.csv`
- [ ] No source text in any released file (candidates and review sheet stay git-ignored)

## Before it goes public
- [ ] `AUTHORS.json`, `LICENSE`, `CITATION.cff`, README maintainer line filled
- [ ] README, LIMITATIONS, CODEBOOK rewritten in your own voice
- [ ] Figures regenerated with `--final`; all DRAFT banners removed; `tools/publish_gate.py .` passes
- [ ] Zenodo sandbox record reviewed before the real deposit
- [ ] Evidence log row written the day of release
