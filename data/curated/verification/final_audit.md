# Independent audit: PhotoDeg-Bench v1.0 release candidate

Auditor: independent AI auditor (Claude), 2026-10-12. Not involved in building the dataset. No project file was changed except this report. Note: I re-ran `code/curation/verify_records.py` once to reproduce its numbers; it rewrites `data/curated/verification/deterministic.jsonl`. The new file is byte-identical to the original (checked with `cmp` against a backup); only its modification time changed.

## Verdict: NOT READY. The fixes are small and can be done quickly.

The records hold up well. In 12 sampled records, every number and condition I checked matches the source. The problems that block release are elsewhere:

- **Screening.** The E2 exclusion code is a keyword fall-through, and the methods text describes it falsely.
- **License text.** The LICENSE says something the release contents contradict.
- **Release bundle.** The bundle does not contain the code the README and Zenodo text say it contains.

Every one of these can be fixed without touching any record values.

## Findings

| # | Severity | Location | Evidence | Suggested fix |
|---|---|---|---|---|
| 1 | **Critical** | `code/curation/screen_decisions.py` `title_code()` and `main()`; `screening_log.csv` (332 E2 rows, all `stage=title`, `confidence=high`); METHODS "Every title was read" | Any paper not in a hand-written index list falls through to E2, and the rationale is chosen by keyword. The result is clear E2 errors on synthetic-plastic photodegradation papers: #164 "Photocatalytic Degradation of HDPE Microplastics Using C,N-TiO2" (open full text, PMC8037624); #550 "Photocatalytic degradation of polyethylene films…" (PMC13139506); #418 "…Photocatalytic Properties of Iron Vanadate… Degradation of Microplastics" (PMC12392196); #465 "…Photocatalytic Oxidation Activity of Nanoplastics and Methylene Blue", coded "small-molecule pollutant" because the title contains "methylene"; #381 "…Carbon Nitride Upcycles Plastic Wastes for… Acetic Acid" (abstract: "CH3COOH yield… from PVC… PE… PET… PP… under AM1.5G"); #523 "visible-light-driven degradation of polystyrene microplastics"; #320 "…efficient PET plastics removal"; #149, #376, #397 (photoreforming, which should be E4 by the stated convention); #342, #501, #575 (reviews, which should be E1). About 28 E2 titles match plastic and degradation keywords. The four open-full-text papers above were never assessed against E5/E6. | Re-screen all 332 E2 papers against the abstract. Recode them (E1, E4, E5 or E6), assess #164, #418, #465 and #550 on full text, and regenerate the flow figure and stats. Replace "high" confidence on default codes with "default/keyword". Correct the "Every title was read" claim, or make it true. |
| 2 | Major | Screening codes E3 and E4 (same file) | #16 is coded E3 although its abstract says "Xenon lamp". ELIGIBILITY.md explicitly passes "Xe lamp without a UV cut-on restriction". #601 is coded E3 although it includes "natural weathering on the rooftop" (sunlight). The E3 rationale "(or no visible component stated)" is broader than the written criterion. #13 (PHA, a biopolymer) is coded E4, but by the first-failing rule it should be E2. The final outcome (excluded, most likely on E5) is probably unchanged. | Recode these. Make the E3 rationale match the criterion. |
| 3 | Major | `LICENSE` ("The release contains reported experimental values and locators, not text from the source articles") vs `evidence.csv` and `extractions/*.json` in the release bundle | `evidence.csv` carries a verbatim `source_string` for 1,411 fields, and notes quote sources. 47 of 87 records come from CC BY-NC (31) or CC BY-NC-ND (16) articles, e.g. PMC12056016 and PMC13590609, which are by-nc-nd/4.0 in their own XML. R14 itself admits "short source strings in evidence.csv". The whole dataset is relabelled CC BY 4.0. | Correct the LICENSE wording. Either carve out the source strings from NC/ND articles (separate license, or locators only) or get the R14 author decision before release. |
| 4 | Major | `release/photodeg-bench-v1.0.0.zip` (63 files) | The bundle has no `code/`, `tools/`, `tests/` or `requirements.txt`. The README "Run it" section, the Zenodo description ("Contents: … code") and the LICENSE MIT clause all assume the code is there. The bundle also lacks `docs/NEXT_STEPS.md` and `PUBLISH_GUIDE.md`, which are linked from the docs. | Include the code in the deposit, or change the README and Zenodo text. |
| 5 | Major | LIMITATIONS §1, README, `stats.json` (`n_in_scope_no_fulltext` 54, share 0.75) | Of the 54 E6 papers, #229 is a duplicate of #227 and #587 a duplicate of #545. #305 is "publisher record of PMC11796324, which is processed", so it is in the dataset, not lost. Several more (#60, #445, #210, #251) are noted as "likely" failing E5. The headline "75% of in-scope papers" is inflated. Finding 1 will also change this number. | Deduplicate, then recompute the count and the share. |
| 6 | Minor-major | `build_records.py` FLAG_RULES (regex on notes) | The pattern `thermal\|…\|heating` matches the note "LED heating, no external heat". As a result all 9 PMC10793207 records at ~35 °C (rows 9 and 15 included, controls included) are flagged `thermal_contribution`, so 9 of the 15 flags in LIMITATIONS §8 are false positives. Row 15 (PMC10793207-g) takes its time (24 h), solvent and O2 from the entry-1 text but has no `standard_conditions_applied` flag, while row 9 has it. | Set the flags from structured fields, or review each flag by hand. |
| 7 | Minor | Row 37, PDG-PMC12056016-g | `irradiance` = 0.4 W/cm² was taken from the PS optimisation paragraph ("still furnishing 50% isolated yield of BA from 0.10 g of PS1 using a 405 nm LED (0.4 W/cm2)"). That is a different experiment. The light and atmosphere locators point to "General procedure… upcycling of PS", although the Fig. 6/7 procedure ("irradiated with a 50 W 405 nm LED light, while kept sparging with a gentle flow of air") is the correct source. The values are the same. | Re-point the locators. Drop the irradiance or mark it as borrowed. |
| 8 | Minor | Row 66, PDG-PMC13590609-h | `atmosphere=air` cites the PP-only paragraph ("at 130 °C in air"). The co-cycling Methods say the reaction ran in "a thick-walled pressure-resistant bottle", so the atmosphere is not stated for this run. The light locator is "Preparation of OPPs" rather than "Co-cycling of PP and PET" (same values). Scope: PET is cleaved by the HCl this process releases at 130 °C. This is admissible as a tandem step because the no-light control gives 0% TPA, but it deserves a scope note. | Leave the atmosphere blank, or call it "sealed (air headspace)". Fix the locator and add a scope flag. |
| 9 | Minor | Row 44, PDG-PMC12302232-g | The note says the run was "under the optimized/standard reaction conditions". The EPS sentence itself ("Additionally, EPS waste, such as foam boxes… producing benzoic acid in 57% yield") does not say this. The phrase "under standard conditions" belongs to the preceding PS-waste sentence. The inference is reasonable but the quotation is wrong. | Reword the note so the inference is not presented as a quote. |
| 10 | Minor | Rows 22, 66, 81 (and others) | The `irradiance` column holds electrical LED power (50 W, 14.4 W), and the unit field says so. This is still a misuse of a column named irradiance. | Rename the column to `lamp_power`, or move these values to a separate field. |
| 11 | Minor | Row 81, PDG-PMC9295126-o | `catalyst_loading` = 20 mol% applies to NHPI only, but the catalyst field reads "NHPI + carbon nitride". | Note in the record that the loading is NHPI only. |
| 12 | Minor | Row 3 and about 15 other records | `time_unit` is filled ("min", "h") while `time` is empty: there are 86 `time_unit` inferences but only 71 `time_h` values. | Leave the unit blank when there is no value. |
| 13 | Minor | README "87 verified records"; Zenodo "Every value carries its locator and source string" | 389 fields are "inferred" and have no locator. These include `yield_basis` (18) and `sec_calibration` (17), which are substantive. `blind_verified=y` means only that a blind pass exists (`key in covered`), not that it agreed. Human review is correctly disclaimed everywhere. | Use "source-checked" in place of "verified". Correct the Zenodo sentence. Consider dropping `yield_basis` and `sec_calibration` from INFERABLE. |
| 14 | Minor | HARMONIZATION_REPORT table; README "Fifteen documented rules" | The yaml has 15 rules, but the table omits R04 (Mark–Houwink). R15 labels 50 °C runs (14 records) "ambient". | Add R04 to the table. Rename the class to "near-ambient (<60 °C)". |
| 15 | Minor | `tools/release_gate.py`, `zenodo_deposit.py` | Publishing is correctly refused without `release/AUTHORIZATION.json` plus a passing gate. However, the "signed" authorization is only checked for four non-empty keys, so anyone or any agent could write the file. `zenodo_deposit.py` without `--publish` uploads a draft to production Zenodo with no authorization check. The A1 detail message checks only AUTHORS.json. | Describe the authorization accurately (it is not signed), or add a real check. Require authorization for any non-sandbox upload. |
| 16 | Minor | PMC10793207 license | "cc by-nc" comes from Europe PMC metadata. The XML itself has only "© The Royal Society of Chemistry". | Confirm the license on the publisher page and record where it came from. |
| 17 | Minor | PMC10793207-e (row 13) `is_control=y` | The paper's text calls only entries 2–4 "Control experiments". Entry 5 (no HCl, 20% BA) is an ablation, not a control. | Consider setting it to n, or add a vocabulary note for omission runs. |

## What I checked and found correct

**Record accuracy (12 records).** In all 12 records, every recorded numeric value matched the source text at its locator, and so did polymer identity, before/after averages, time, temperature, catalyst and loading, wavelength, solvent and yields with their basis:

| Row | Record | What it holds |
|---|---|---|
| 3 | PMC10557129-c | 6%, 100 °C, dark, 1 equiv FeCl2 |
| 9, 15 | PMC10793207-a, -g | Table 1 entries 1 and 7: 33% and 50% BA, 10/5 mol%, HCl 10/500 mol%, 390 nm, O2, ~35 °C from footnote a, 24 h from text |
| 22, 30 | PMC11796324-e, -m | Table 1 entries 5 and 13: Mn 99 000 → 528 / 450 with Đ 5.10 / 6.05, GC-FID yields (no [d] marker), air / Q-sun 44 h, 1–2 mol% |
| 37 | PMC12056016-g | 93% isolated TPA. Loading and time were correctly left out because footnotes h and j are ambiguous |
| 44 | PMC12302232-g | 57% foam box |
| 51, 58 | PMC12464638-e, -l | Table 2 entry 5 at 66% with the footnote-a conditions; 81% with PS added; time correctly left out |
| 66 | PMC13590609-h | 91.1% for the PET bottle/PP jug pair, 130 °C, 18 h, 415 nm |
| 73, 81 | PMC9295126-f, -o | Entries 8 and 15: 0% (dark, 50 °C) and 5.5%, 16 h and 2 mL EtOAc from the footnote; the carbon-nitride amount conflict is correctly noted |

The `is_control` flags in the sampled records are correct; finding 17 concerns a record outside the sample. Mn vs Mw is assigned correctly wherever molar masses are present. `evidence.csv` agrees exactly with the released CSV across all 1,800 fields.

**Screening.** These exclusion codes are right:

- E2: #0, #103, #245, #421, #600
- E1: #14, #365, #599
- E4: #390 and #597 (debatable; both fail E5 anyway)
- E6: #51, #593

**Counts.** These match `stats.json` and the data:

- 87 records, 10 papers, 20 controls, 29 molar-mass pairs, 75 yield records
- License split 40/31/16
- Polymer, calibration, band, thermal and tier tallies
- QA flag totals
- 1,800 / 1,411 / 389 field outcomes, reproduced by re-running `verify_records.py`
- Blind comparison 1,248 / 183 / 99 / 36
- 43 adjudications
- 109 excluded observations
- 18 full-text decisions (10 include, 4 E5, 3 E6, 1 E4)

**Verification and release code.**

- `verify_records.py` does what METHODS says: it checks that the locator exists, that the source string occurs there after normalisation, and that the number equals the value for numeric fields. Text fields are only string-checked, which METHODS also says. No `scale` overrides are used.
- None of the 183 blind disagreements on numeric or condition fields is left unadjudicated except paraphrases (abbreviations of the solvent field).
- `publish_github.py`, `zenodo_deposit.py --publish` and `autonomous_release.py --publish` all refuse to publish without the authorization file and `release_gate.py --mode publish`.
- AI curation and the absence of human review are disclosed in the README, METHODS, LIMITATIONS, CITATION.cff and the Zenodo metadata.
- The release bundle data files are identical to the working copies.
