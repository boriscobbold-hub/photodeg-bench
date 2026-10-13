# Independent audit, round 2: PhotoDeg-Bench v1.0 release candidate

Auditor: the same independent AI auditor as round 1 (Claude), 2026-10-13. No project file was changed except this report. I re-ran the pipeline in a scratch copy of the repository, not in the project itself:

- `verify_records.py` gave 1792 fields: 1411 matched and 381 inferred. Its `deterministic.jsonl` is byte-identical to the project's.
- `build_records.py` produced identical `records.csv`, `evidence.csv` and `qa_flags.csv`.
- `screen_decisions.py` produced an identical `screening_log.csv`.
- The unit tests pass (25 of 25).

Process note: the baseline commit 9b9864f, labelled "pre-audit-fix checkpoint", already contains `RESCREEN`/`DUPLICATES` and the five new extraction files. `git diff 9b9864f` therefore understates the fixes. I judged the current working tree.

## Verdict: ready with fixes

Every fix to record values holds, and the screening problem (round-1 finding 1) is resolved. What remains is packaging and wording: the license exception is incomplete for some files in the bundle, the bundle cannot rebuild itself, and two locators are still wrong. None of these changes a value. Once they are fixed, the release is ready for the author's authorization (A1–A3, which are still pending).

## (a) Round-1 findings: status

| # | Status | Evidence |
|---|---|---|
| 1 E2 fall-through | **Fixed** | `RESCREEN` (60 changes), 5 papers moved to full text, `DUP` code, default confidence now "medium (title-level category)". Screening log reproduces: E2 294, E1 126, E4 73, E6 64, E3 20, E5 8, include 10, DUP 7. Residue: METHODS and the `title_code` docstring still say "All 602 titles were read". |
| 2 E3/E4 miscodes | **Fixed** | #16 and #601 → E6, #13 → E2. E3 rationale is now "UV-only irradiation stated in the abstract". |
| 3 License vs strings | **Partly fixed** | `evidence.csv` now gives a SHA-256 instead of the string for NC/ND sources, and LICENSE was rewritten. Problems remaining: (i) the bundle's `verification/deterministic.jsonl` holds 277 NC/ND lines with the plain source string `s` (e.g. PMC12056016-a `"s": "phenothiazine derivative, PTH-3CN"`), and `verification/blind/*.json` holds verbatim strings too. LICENSE names only the extraction files as an exception. (ii) `zenodo_metadata.json` declares only `cc-by-4.0`. (iii) "anyone can check [the hash] against a re-fetched copy" works only if the checker knows the exact substring. |
| 4 Bundle lacks code | **Partly fixed** | `code/`, `tools/`, `tests/`, `requirements.txt` and `Makefile` are now included. Still missing: `verification/blind_coverage.json` (read by `build_records.py` line 73), `data/curated/license_check.csv` (without it, gate check S9 reports every article "unchecked") and `verification/final_audit.md` (cited in the README and METHODS). As a result, the pipeline cannot be rerun from the deposit. |
| 5 In-scope count | **Fixed** | Duplicates are coded DUP. 61 papers / 0.726 is consistent with 61 / (61 + 23). |
| 6 Regex flags | **Fixed** (residue) | Flags are now structured. `thermal_contribution` drops from 15 to 2; the 35 °C false positives are gone. Residue: `conditions_from_other_block` is set on 72 of 87 records, so it says little. The thermal rule uses yields only, so it misses molar-mass dark controls. Example: PMC13590609-c, dark, Mn 45.7 → 30.8 kDa, against lit -a at 14.7 kDa. The flag was also lost on PMC9586668-e, whose note says "authors note heat contributes". |
| 7 Row 37 | **Partly fixed** | The irradiance was removed (adjudication "audit correct"). `light_source`, `wavelength_nm` and `atmosphere` still cite "General procedure… upcycling of PS ¶1" instead of the Figs. 6/7 procedure. |
| 8 Row 66 | **Partly fixed** | The atmosphere was blanked for d–i and a scope note added. The light fields still cite "Preparation of OPPs ¶1". |
| 9 Row 44 note | Fixed | |
| 10 Irradiance column | Partly fixed | A `light_quantity_type` column (lamp_power or irradiance) was added. The column is still named `irradiance`. Acceptable. |
| 11 NHPI loading | Fixed | |
| 12 Units without a value | Fixed | `build_records` now blanks the unit when there is no value. |
| 13 Overstated verification | Fixed | Wording is now "source-checked". `ABSENCE_ONLY` lets `sec_calibration` and `yield_basis` go without a locator only when stating they are absent. Zenodo wording corrected. |
| 14 R04 / ambient | Fixed | |
| 15 Gate wording, Zenodo drafts | Fixed | The docstring states the file is not a signature. Any non-sandbox Zenodo upload now requires authorization. |
| 16 PMC10793207 license | Fixed | `license_check.csv`: all 10 articles agree with Crossref, and S9 uses it. |
| 17 Entry 5 control flag | Fixed | `is_control=n` with a note; controls now 19. |

## (b) Screening re-check

**10 papers still coded E2 that mention plastics or polymers:** #1, #98, #131, #147, #247, #297, #394, #415, #527, #535. All are correctly excluded. Their substrates are a vacuum residue, a flame-retardant additive, small-molecule photoproducts, BPA or atrazine, or the polymer is a matrix or material. The rationale text for #297 ("small-molecule pollutant") is wrong, but the code is right.

**5 papers coded E6:** #16, #227, #331, #493 and #601 are reasonable: in scope on the abstract, with no full text. #295 and #589 are low-confidence "light source unclear", which is honestly labelled.

**5 papers moved to full text:** each exclusion is justified by the text.

| Paper | Decision | What the full text shows |
|---|---|---|
| PMC8037624 | E5 | 50 W visible LED; only gravimetric loss, carbonyl index and morphology reported |
| PMC12392196 | E3 | PS microplastics irradiated only at "365 nm (λmax) UVA light (8 W)"; the Xe lamp was used only for bacteria |
| PMC12566621 | E5 | Xe lamp with AM1.5G filter; only particle size, FTIR and TOC reported |
| PMC13139506 | E5 | Sunlight; only weight loss and CO2-C reported |
| PMC13051431 | E5 | 400 W metal lamp; only mass loss, FTIR, CO2 and TOC reported |

## (c) Six new records: all correct against the source

| Row | Record | What I checked |
|---|---|---|
| 2 | PMC10557129-b | 88%, dark, 170 °C |
| 18 | PMC11796324-a | Table 1 entry 1: 99 000 / 1.98 → 213 / 3.10; 18.2% and 2.1% by NMR (footnote [d]); 2 mol%, 24 h, O2 |
| 40 | PMC12302232-c | EPS, 56%, "under the optimized reaction conditions" (¶7) |
| 55 | PMC12464638-i | Table 2 entry 9, no light, 0%; conditions from footnote a |
| 70 | PMC9295126-c | 30% BA; CO 21% and CO2 7.5% ("Gaseous CO (21% yield) and CO2 (7.5% yield)… after 16 h"); 50 °C |
| 86 | PMC9586668-d | Table 2 r2: 56 000 → 41 000, Đ 1.3 → 1.7, 90 °C, 6 h, toluene |

## (d) Problems introduced by the fixes

| Severity | Location | Issue | Fix |
|---|---|---|---|
| Major | Bundle `verification/` and LICENSE | Unhashed NC/ND source strings ship in `deterministic.jsonl` and `blind/*.json`, which the LICENSE exception does not cover. This undoes the purpose of hashing. | Hash or strip `s` for NC/ND papers in those files, or extend the LICENSE exception and Zenodo text to name them |
| Minor | Bundle | `blind_coverage.json`, `license_check.csv` and `final_audit*.md` are missing, so the deposit cannot rerun or pass its own gate | Add them to `build_release.py` |
| Minor | LIMITATIONS §2; METHODS "Independent final audit" | Says "no value errors" / "(all values correct)". Round 1 found no numeric errors but did find attribution issues (rows 37 and 66, now fixed). | Say "no numeric errors; three attribution issues found and fixed" |
| Minor | METHODS; `screen_decisions.py` docstring | "All 602 titles were read" is not demonstrable for category-coded titles | Drop the claim or qualify it |
| Minor | `thermal_contribution` rule | Ignores molar-mass dark controls (PMC13590609-a/-b vs -c) | Extend the rule to retained fraction, or flag these records by hand |

**Numbers checked and consistent:** README, LIMITATIONS, METHODS and HARMONIZATION figures all match `paper/stats.json` and the data: 87 records, 19 controls, 29 molar-mass pairs, 75 yield records, 1792/1411/381 fields, 1241/184/97/36 blind comparison, 52 adjudications, 121 excluded observations, 61 papers / 73% lost to access, flag counts, thermal regimes, and title/abstract and full-text screening counts. The flag definitions in VOCABULARIES.md match the code. The release bundle data and docs are identical to the working copies.
