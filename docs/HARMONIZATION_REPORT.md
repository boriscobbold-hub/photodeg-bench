# Harmonization report, v1.0

Rules and their full rationale live in [rules/harmonization.yaml](../rules/harmonization.yaml); `code/04_harmonize.py` executes them and refuses to run if any required rule is unset. As-reported values are always kept beside harmonized ones. The rules were set by the AI curator under delegation; R08 (scope of "visible light") and R14 (source licenses) are escalated to the author and run on conservative provisional settings.

| Rule | Decision | Why, in one line |
|---|---|---|
| R01 unit | kg/mol | unit conversion only |
| R02 primary average | M<sub>n</sub>, else M<sub>w</sub>; never mixed within a pair | M<sub>n</sub> tracks chain number; some papers report only M<sub>w</sub> |
| R03 calibration | keep as reported, label class | universal calibration (ISO 16014-2) needs Mark–Houwink constants not established for degraded, end-functionalized oligomers |
| R05 calibration class | absolute / matched / mismatched / unknown / not applicable | conventional calibration is exact only for the standard's own polymer |
| R06 metrics | retained fraction, percent reduction | scissions per chain omitted: it assumes random scission, while several systems unzip from chain ends |
| R07 basis | same average, same SEC method | holds within every record |
| R08 visible window | 380–780 nm; broadband/solar/Xe kept and flagged | CIE colorimetric range; *escalated* |
| R09 bands | violet 380–450, blue 450–495, green 495–570, yellow–red 570–780; colour-only by name; broadband | conventional colour boundaries |
| R10 time | hours | |
| R11 tiers | separate ladders: MM-A/B/C for molar mass, PY-A/B/C for yields | different endpoints are never merged |
| R12 yield basis | kept as reported | conversion needs data papers do not give |
| R13 controls | released, flagged, kept out of performance figures | they show whether light and catalyst matter |
| R14 licenses | all CC variants kept, license per row | *escalated*: NC/ND sources are a legal call |
| R15 thermal regime | ambient <60 °C, heated 60–120, high >120 | stops photothermally assisted runs being ranked with ambient ones |

## Effect on v1.0

- Calibration classes: not_applicable 58, unknown 17, mismatched_conventional 8, matched_conventional 4.
- Wavelength bands: blue 48, violet 26, dark 9, broadband 2, unknown 2.
- Thermal regimes: not_reported 44, ambient 24, high_temperature 16, heated 3.
- Molar-mass tiers: missing 58, MM-B 20, MM-C 6, MM-A 3. Product-yield tiers: PY-A 47, PY-B 15, PY-C 13, missing 12.
- Retained fraction, non-control records: median 0.0208, range 0.00187–1.

## Where the rules do not hold

- Cross-paper comparison of absolute molar masses is approximate whenever calibrations differ (most records are "unknown" or "mismatched").
- Retained fraction compares within a record, so a constant calibration bias largely cancels, but a mechanism change (unzipping vs random scission) still makes equal retained fractions mean different things.
- Light dose is not harmonized: reported powers are mostly electrical LED power, not irradiance at the sample.
- Yields with different bases (per repeat unit, isolated, NMR, GC, mass) are not interchangeable; filter on `yield_basis`.
