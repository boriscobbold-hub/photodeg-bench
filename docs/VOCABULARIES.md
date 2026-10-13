# Controlled vocabularies (v1.0)

Used by extraction (as-reported fields) and harmonization (derived fields).


- **polymer** (canonical): `polystyrene`, `poly(methyl methacrylate)`, other poly(meth)acrylates by full name, `polyethylene`, `HDPE`, `LDPE`, `polypropylene`, `poly(vinyl chloride)`, `poly(ethylene terephthalate)`, `poly(lactic acid)`, `polycaprolactone`, `polycarbonate`, `polyurethane`, `polyamide 6`, `polyamide 6,6`, copolymers as `poly(A-co-B)`; designed polymers by the paper's class name (e.g. `polypinacol`).
- **polymer_class**: `vinyl_styrenic`, `vinyl_methacrylate`, `vinyl_acrylate`, `vinyl_halogenated`, `vinyl_ether`, `vinyl_ketone`, `vinyl_other`, `polyolefin`, `polyester`, `polycarbonate`, `polyamide`, `polyurethane`, `polyether`, `polyacetal`, `designed_degradable`, `other`.
- **sec_calibration**: `conventional_PS`, `conventional_PMMA`, `conventional_PEG_PEO`, `universal_calibration`, `absolute_MALS`, `triple_detection`, `high_temperature_SEC`, `MALDI_TOF`, `DOSY_NMR`, `other`, `not_reported`.
- **light_color**: `violet` (380–450 nm), `blue` (450–495), `green` (495–570), `yellow_orange_red` (570–780), `white`, `solar`.
- **atmosphere**: `air`, `O2`, `N2`, `Ar`, `degassed`, `inert (gas not named)`.
- **time_unit**: `s`, `min`, `h`, `d`.

- **calibration_class** (derived, R05): `absolute`, `matched_conventional`, `mismatched_conventional`, `unknown`, `other_method`, `not_applicable`.
- **wavelength_band** (derived, R09): `violet`, `blue`, `green`, `yellow_orange_red`, `broadband`, `dark`, `unknown`.
- **thermal_regime** (derived, R15): `near_ambient` (<60 °C, incl. LED self-heating), `heated`, `high_temperature`, `not_reported`.
- **light_quantity_type** (derived): `irradiance` (power per area at the sample) or `lamp_power` (electrical/optical lamp power); says what the `irradiance` column holds.
- **tier_molar_mass / tier_product_yield** (derived, R11): `MM-A`, `MM-B`, `MM-C` / `PY-A`, `PY-B`, `PY-C`.
- **qa_flags**: `approximate_value` (the number's own source string is approximate), `conditions_from_other_block` (a condition was read from another Results paragraph or another table/figure than the result, typically the paper's own 'standard conditions' statement; Methods procedures and the result's own table notes do not count), `thermal_contribution` (a dark control with the same polymer, temperature, catalyst and loading gives ≥50% of the lit yield, or the paper/verifier states the run is mostly thermal), `heated_ge_80C`, `sec_estimate`, `bimodal_sec`.
- **is_control**: `y` for runs the paper presents as controls (dark, no catalyst, no O2, no substrate); single-component omissions the paper does not call controls are `n` with a note.
- **screening codes**: `include`, `E1`–`E6` (docs/ELIGIBILITY.md), `ambiguous`.
