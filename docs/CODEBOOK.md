# Codebook: photodeg_bench_v1.0.csv

> DRAFT. Definitions of harmonized columns depend on the rules in `rules/harmonization.yaml`; update this file whenever a rule changes.

Columns without `_h` are **as reported** in the source, entered by the curator. Columns ending `_h` and the derived columns below are **computed** by `code/04_harmonize.py`.

## Identity and provenance

| Column | Definition |
|---|---|
| record_id | Stable ID, `PDG-<paperseq>-<n>`; never reused after release |
| paper_id | DOI (lower-case) or PMCID when no DOI; joins to `data/processed/corpus.csv` |
| doi | Source article DOI, bare form `10.xxxx/...` |
| source_license | Article license as recorded by Europe PMC/OpenAlex (e.g. `cc-by`), checked by curator |
| locator | Where the value is in the article: `Table 2 r3`, `Fig. 4 caption`, `SI Table S5 r2`, `Results ¶4` |
| curator, curation_date | Who entered/confirmed the record and when (YYYY-MM-DD) |
| checked_against_source | `y` only after the curator compared every value with the source |

## Polymer

| Column | Definition |
|---|---|
| polymer | Polymer name, canonical form (e.g. `polystyrene`, `poly(methyl methacrylate)`) |
| polymer_class | `vinyl_styrenic`, `vinyl_methacrylate`, `vinyl_acrylate`, `vinyl_halogenated`, `vinyl_other`, `polyolefin`, `polyester`, `polycarbonate`, `polyamide`, `polyurethane`, `polyether`, `biopolymer`, `other` |
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
| sec_calibration | `conventional_PS`, `conventional_PMMA`, `conventional_PEG_PEO`, `universal_calibration`, `absolute_MALS`, `triple_detection`, `high_temperature_SEC`, `MALDI_TOF`, `DOSY_NMR`, `other`, `not_reported` |
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
| product_yields | `name: value unit` items, `;`-separated, e.g. `benzoic acid: 40 %` |
| yield_basis | `mol% per repeat unit`, `wt%`, `isolated`, `NMR`, as reported |

## Harmonized and derived (set by rules)

| Column | Rule | Definition |
|---|---|---|
| mn_before_h … mp_after_h, mass_unit_h | R01, R03, R04 | Masses in the canonical unit; converted or cleared per calibration policy |
| calibration_class | R05 | e.g. absolute / matched_conventional / mismatched_conventional / unknown |
| mass_basis | R03 | `as_reported`, `relative_mismatched`, `universal_conversion`, `conversion_unavailable`, `excluded_mismatched` |
| primary_average, primary_before, primary_after | R02, R07 | Which average is compared and its two values |
| retained_fraction | R06 | primary_after / primary_before |
| percent_reduction | R06 | 100 × (1 − retained_fraction) |
| scissions_per_chain | R06 | M<sub>n,before</sub>/M<sub>n,after</sub> − 1 |
| primary_metric | R06 | The metric used for ranking and figures |
| wavelength_band, light_flags | R08, R09 | Band label; flags `broadband`, `uv_component`, `solar_or_xenon` |
| time_h, time_unit_h | R10 | Time in the canonical unit |
| is_control | R13 | `y` for dark / no-catalyst / no-O<sub>2</sub> controls |
| tier | R11 | Comparability tier; `unranked` if no tier's conditions hold |
