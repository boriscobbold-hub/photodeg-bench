# Limitations

> DRAFT. Written before any analysis so the analysis cannot outrun it. Curator: revise in your own words and add any found during curation.

1. **Open-access only.** Records come from papers with open full text in Europe PMC (or open copies located via OpenAlex). Paywalled work, including much of the early and industrial literature, is absent, so the benchmark is not a census of the field.
2. **Conventional SEC is relative.** Molar masses from calibration against standards of a different polymer are not absolute. Unless a record is converted by universal calibration (with the constants and their sources stated in the rules) or measured by an absolute method, its harmonized mass is a relative value, and the tier says so.
3. **Before/after comparability.** A retained fraction is only meaningful when both points use the same average and the same SEC method; rule R07 states how strictly this is applied.
4. **Light dose is under-reported.** Many papers give electrical lamp power or a colour, not photon flux or irradiance at the sample. Wavelength bands and time are harmonized; dose is not, so records with equal time are not necessarily equal dose.
5. **Extraction recall.** Candidate extraction reads text and tables in JATS XML. Values only in plots or SI PDFs are found only if the curator enters them by hand; the review sheet shows where extraction found nothing.
6. **Product yields are on mixed bases** (mol% per repeat unit, wt%, NMR vs isolated). Rule R12 states whether they are converted.
7. **Single curator.** Every record is checked by one curator. A second-curator check of a random sample is planned for a later version (see NEXT_STEPS).
8. **Publication bias.** Successful conditions are reported more than failures; controls and negatives are kept where reported (R13) but the benchmark over-represents positive results.
