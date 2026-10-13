# Codebook: photodeg_bench_v1.0.csv

> Harmonized columns follow `rules/harmonization.yaml` v1.0. Controlled vocabularies: [VOCABULARIES.md](VOCABULARIES.md).

Columns without `_h` are **as reported** in the source, entered by the curator. Columns ending `_h` and the derived columns below are **computed** by `code/04_harmonize.py`.

## Identity and provenance

| Column | Definition |
|---|---|
| record_id | Stable ID `PDG-<PMCID>-<letter>`; never reused after release |
| pmcid | PubMed Central ID of the full text that was read |
| is_control | `y` for dark / no-catalyst / no-O<sub>2</sub> / no-additive runs |
| paper_id | DOI (lower-case) or PMCID when no DOI; joins to `data/processed/corpus.csv` |
| doi | Source article DOI, bare form `10.xxxx/...` |
| source_license | Article license as recorded by Europe PMC/OpenAlex (e.g. `cc-by`), checked by curator |
| locator | Where the record's main result is in the article (`Table 2 r3`, `Results ¶4`); per-field locators are in `data/curated/evidence.csv` |
| curator, curation_date | `Claude (AI) autonomous curation`, date |
| extractor, extraction_method | Which extraction agent, and whether values came from tables and/or text |
| source_verified | `y` = every field's source string was found at its locator and its number matches (deterministic check) |
| blind_verified | `y` = an independent blind re-extraction covered the record and no substantive disagreement is unresolved |
| qa_flags | `;`-separated: `approximate_value`, `standard_conditions_applied`, `thermal_contribution`, `heated_ge_80C`, `sec_estimate`, `bimodal_sec` (evidence in `data/curated/qa_flags.csv`) |

## Polymer

| Column | Definition |
|---|---|
| polymer | Polymer name, canonical form (e.g. `polystyrene`, `poly(methyl methacrylate)`) |
| polymer_class | see VOCABULARIES.md |
| polymer_detail | Free text: tacticity, end groups, commercial grade, post-consumer source, film/powder |

## Molar mass (as reported)

| Column | Definition |
|---|---|
| mn_before, mw_before, mp_before | Number-, weight-, peak-average molar mass before irradiation |
| disp_before | Dispersity Đ (M<sub>w</sub>/M<sub>n</sub>) before |
| mass_unit_before | `kg/mol`, `g/mol`, `kDa`, `Da` |
| mn_after, mw_after, mp_after, disp_after, mass_unit_after | Same, after irradiation for `time` |

## SEC method

| Column | Definition |
|---|---|
| sec_calibration | see VOCABULARIES.md; `not_reported` when the paper states none |
| sec_detector | e.g. RI, UV, MALS, viscometer |
| sec_eluent | e.g. THF, chloroform, DMF + LiBr, TCB |
| sec_temperature_c | Column temperature, °C |

## Reaction conditions

| Column | Definition |
|---|---|
| catalyst, catalyst_loading, catalyst_loading_unit | Photocatalyst/catalyst as named; loading and unit (`mol%`, `wt%`, `mg`, `equiv`) |
| cocatalyst_additives | Other additives (HAT co-catalyst, acid, base, oxidant) |
| light_source | e.g. `Kessil PR160L`, `LED strip`, `solar simulator` |
| wavelength_nm | Peak/nominal wavelength, nm |
| wavelength_range_nm | Band as `lo-hi` when a range is reported |
| light_color | Colour as reported when no wavelength is given |
| irradiance, irradiance_unit | As reported (`mW/cm2`, `W/m2`, or electrical `W`) |
| solvent, concentration, concentration_unit | Reaction medium and polymer concentration |
| atmosphere | `air`, `O2`, `N2`, `Ar`, `degassed`, as reported |
| temperature_c | Reaction temperature, °C (25 for "room temperature" unless stated) |
| time, time_unit | Irradiation time and unit (`s`, `min`, `h`, `d`) |

## Products

| Column | Definition |
|---|---|
| products | Named products, `;`-separated |
| product_yields | `name: value unit` items, `;`-separated, e.g. `benzoic acid: 40 %`; units `%`, `mol%`, `wt%` or an amount (`mg`) |
| yield_basis | How the paper defines the yield (per repeat unit, isolated, NMR, GC-FID, ...) |
| yield_uncertainty | Per-product uncertainty as printed (e.g. `± 2 (SD, n=3)`) |
| replicates | Number of replicates when stated |

## Harmonized and derived (set by rules)

| Column | Rule | Definition |
|---|---|---|
| mn_before_h … mp_after_h, mass_unit_h | R01, R03, R04 | Masses in the canonical unit; converted or cleared per calibration policy |
| calibration_class | R05 | absolute / matched_conventional / mismatched_conventional / unknown / other_method / not_applicable (no molar mass) |
| mass_basis | R03 | `as_reported`, `relative_mismatched`, `universal_conversion`, `conversion_unavailable`, `excluded_mismatched` |
| primary_average, primary_before, primary_after | R02, R07 | Which average is compared and its two values |
| retained_fraction | R06 | primary_after / primary_before |
| percent_reduction | R06 | 100 × (1 − retained_fraction) |
| primary_metric | R06 | The metric used for ranking and figures |
| wavelength_band, light_flags | R08, R09 | `violet`/`blue`/`green`/`yellow_orange_red`/`broadband`/`dark`/`unknown`; flags `broadband`, `uv_component`, `solar_or_xenon` |
| thermal_regime | R15 | `ambient` (<60 °C), `heated` (60–120), `high_temperature` (>120), `not_reported` |
| time_h, time_unit_h | R10 | Time in the canonical unit |
| is_control | R13 | `y` for dark / no-catalyst / no-O<sub>2</sub> controls |
| tier_molar_mass | R11 | MM-A (absolute/matched calibration, time, wavelength), MM-B (time, wavelength), MM-C (before/after only) |
| tier_product_yield | R11 | PY-A (time, wavelength, yield basis), PY-B (time), PY-C (yield only) |
