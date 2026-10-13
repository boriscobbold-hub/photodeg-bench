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
- **thermal_regime** (derived, R15): `ambient`, `heated`, `high_temperature`, `not_reported`.
- **tier_molar_mass / tier_product_yield** (derived, R11): `MM-A`, `MM-B`, `MM-C` / `PY-A`, `PY-B`, `PY-C`.
- **qa_flags**: `approximate_value`, `standard_conditions_applied`, `thermal_contribution`, `heated_ge_80C`, `sec_estimate`, `bimodal_sec`.
- **screening codes**: `include`, `E1`–`E6` (docs/ELIGIBILITY.md), `ambiguous`.
