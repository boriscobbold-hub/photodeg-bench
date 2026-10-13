# Extraction protocol (Agent C)

Every record in PhotoDeg-Bench is written as JSON in `data/curated/extractions/<PMCID>.json` and must pass `code/curation/verify_records.py`. Two worked examples: `PMC9586668.json` (SEC table) and `PMC9295126.json` (product yields, controls).

## Ground rules
1. **Read the source, never infer a number.** Every value comes from the article text or a table, with its locator and the literal string it was read from.
2. **Locators** are exactly those printed by `python code/curation/evidence_pack.py <PMCID>`: a section path with paragraph number (`Results and Discussion ¶2`), a caption (`Figure 2 caption`), a table (`Table 1`), a table footnote (`Table 1 footnote`), a cell (`Table 1 r3 c4`, rows counted after the header, columns from 1) or a header cell (`Table 1 h c4`). Use the label exactly as printed, including any trailing period (`Table 1.`).
3. **`s` is the literal source string** at that locator that shows the value (keep it short: the number with its immediate context, e.g. `"3,200 (4 h)"`). The verifier checks `s` occurs at `loc` and that the number in `s` equals `v`.
4. **Only these fields may be `inferred`** (no locator, a reason instead): `polymer_class`, `mass_unit_before/after`, `light_color`, `sec_calibration`, `yield_basis`, `time_unit`, `catalyst_loading_unit`, `irradiance_unit`, `concentration_unit`. A mass unit may be inferred as g/mol only when the paper prints none; say so. `sec_calibration` may be inferred only as `not_reported`.
5. **Do not record** values only in figures (plots), only in SI, given only as ranges, or whose catalyst/polymer identity is only a letter/number defined in a figure. List each under `excluded_observations` with the reason.
6. **One record = one polymer sample × one condition set × one time point.** A paper's table of 6 entries is up to 6 records. Shared conditions go in `shared`; a record overrides any shared field, and `null` removes it.
7. **Controls** (dark, no catalyst, no O<sub>2</sub>, no additive) are records with `"is_control": true` and a `notes` string starting `control:`.
8. **Molar mass**: record the average exactly as reported (`mn_*`, `mw_*`, `mp_*`), with its unit. Never convert, never compute Đ, never take values off a GPC trace.
9. **Product yields**: `product_yields` is a list of `{product, v, u, loc, s, name_loc, name_s, uncertainty?}`. `u` is `%` unless the paper uses mol%, wt% or an amount (`mg`, `µmol`). Record `yield_basis` (how the paper defines the yield).
10. **Uncertainty and replicates**: record `replicates` and per-yield `uncertainty` only when the paper states them.
11. **Screening**: every file has `screen` with `decision` (`include` / `exclude` / `ambiguous`), `criteria` (E-code from docs/ELIGIBILITY.md), `rationale`, `evidence_loc`, `confidence`. A paper that fails E5 or E6 after reading the full text gets a file with `decision: exclude` and no records.

## Controlled vocabularies

- **polymer** (canonical): `polystyrene`, `poly(methyl methacrylate)`, other poly(meth)acrylates by full name, `polyethylene`, `HDPE`, `LDPE`, `polypropylene`, `poly(vinyl chloride)`, `poly(ethylene terephthalate)`, `poly(lactic acid)`, `polycaprolactone`, `polycarbonate`, `polyurethane`, `polyamide 6`, `polyamide 6,6`, copolymers as `poly(A-co-B)`; designed polymers by the paper's class name (e.g. `polypinacol`).
- **polymer_class**: `vinyl_styrenic`, `vinyl_methacrylate`, `vinyl_acrylate`, `vinyl_halogenated`, `vinyl_ether`, `vinyl_ketone`, `vinyl_other`, `polyolefin`, `polyester`, `polycarbonate`, `polyamide`, `polyurethane`, `polyether`, `polyacetal`, `designed_degradable`, `other`.
- **sec_calibration**: `conventional_PS`, `conventional_PMMA`, `conventional_PEG_PEO`, `universal_calibration`, `absolute_MALS`, `triple_detection`, `high_temperature_SEC`, `MALDI_TOF`, `DOSY_NMR`, `other`, `not_reported`.
- **light_color**: `violet` (380–450 nm), `blue` (450–495), `green` (495–570), `yellow_orange_red` (570–780), `white`, `solar`.
- **atmosphere**: `air`, `O2`, `N2`, `Ar`, `degassed`, `inert (gas not named)`.
- **time_unit**: `s`, `min`, `h`, `d`.
