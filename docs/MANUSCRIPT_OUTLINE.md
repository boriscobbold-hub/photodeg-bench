# Suggested data-descriptor outline (e.g. Scientific Data, Data in Brief, or a ChemRxiv preprint)

An outline for the author to write from, not a manuscript. Numbers will come from `paper/stats.json` at writing time.

1. **Title.** PhotoDeg-Bench: a source-verified benchmark of visible-light polymer deconstruction.
2. **Background and summary.** The comparability gap (calibrations, light reporting, yield bases); why a yardstick helps scale-up decisions.
3. **Methods.**
   3.1 Corpus and search strings (Europe PMC, OpenAlex), fetch date, 691 papers.
   3.2 Eligibility criteria E1–E6; screening flow (Figure 1).
   3.3 AI-assisted extraction with locators and source strings; recording rules.
   3.4 Verification: deterministic source matching, blind independent re-extraction, adjudication. State plainly that curation was AI-performed.
   3.5 Harmonization rules and comparability tiers.
4. **Data records.** Files, formats, codebook; 87 records (29 molar mass, 75 yields, 20 controls).
5. **Technical validation.** Field-level verification outcomes; blind agreement and adjudications; QA checks; figure reproduction; a planned human audit of a seeded sample (strongly recommended before journal submission).
6. **Usage notes.** Filtering by tier, calibration class, thermal regime and QA flags; no cross-calibration comparison of absolute masses; the access bias.
7. **Figures.** (1) selection flow; (2) molar-mass retention vs time; (3) benzoic acid yields from polystyrene by study; (4) composition.
8. **Code availability.** Repository and archived release.
9. **Limitations** (from docs/LIMITATIONS.md).
10. **Author contributions and AI disclosure.** State the delegation and what the author did personally; follow the venue's AI policy.
