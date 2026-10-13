# PhotoDeg-Bench build spec

> The spec for the build. Updated 2026-10-12 when curation was delegated to the automated workflow.

```
PROJECT:        PhotoDeg-Bench v1.0. Archetypes: benchmark (4) stacked on dataset (1);
                optional data-descriptor paper (8) once v1.0 is released.

QUESTION:       Under comparable conditions, how much does each visible-light photochemical
                route reduce a polymer's molar mass, and what does it turn the polymer into?

SOURCES:        1. Europe PMC REST API (search + fullTextXML), https://www.ebi.ac.uk/europepmc/webservices/rest/
                   Open-access subset only (OPEN_ACCESS:y). Metadata CC0; article text under
                   each article's own license (recorded per record).
                2. OpenAlex API, https://api.openalex.org/works  (metadata CC0), filter is_oa:true.
                   Used to widen recall and to resolve DOI, license and OA location; full text is
                   taken only where Europe PMC holds the OA JATS XML.
                Vintage: date of the fetch run, written to data/raw/PROVENANCE.txt.
                Access date for v1.0 corpus: 2026-10-12 (run in the build workspace; hashes in PROVENANCE.txt).

UNIT:           One experiment = one polymer sample x one condition set x one reported timepoint
                in one source paper (record_id). Several records per paper are normal.

MEASURES:       Per record, as reported: polymer, polymer class, initial Mn/Mw/Mp/Đ, final
                Mn/Mw/Mp/Đ, SEC calibration type, detector, eluent, catalyst/photocatalyst and
                loading, light source and wavelength (peak or band), irradiance if reported,
                solvent, concentration, atmosphere, temperature, time, product slate (named
                products with yields). Derived (only after Boris sets the rules):
                harmonized molar masses, retained-Mn fraction, scissions per chain, wavelength band,
                time in hours, comparability tier.

OUTPUTS:        data/processed/photodeg_bench_v1.0.csv     harmonized records (release table)
                data/processed/photodeg_bench_v1.0.parquet same, typed
                data/processed/qa_report.txt              QA report
                paper/stats.json                          every number any document quotes
                paper/figures/*.png|svg                   benchmark figures
                docs/CODEBOOK.md, LIMITATIONS.md, VERIFY_CHECKLIST.md, NEXT_STEPS.md
                docs/PUBLISH_GUIDE.md                     Zenodo + GitHub steps

VENUES:         1. GitHub repository, tagged v1.0.0
                2. Zenodo (dataset, versioned DOI; GitHub integration for later versions)
                3. Optional: data descriptor (Scientific Data / Data in Brief / ChemRxiv preprint)

VERIFY POINTS:  (2026-10-12: delegated to automated curation; see docs/METHODS_AUTOMATED_CURATION.md)
                - Rules set by the AI curator; R08 and R14 escalated to the author
                - Records verified deterministically and by blind re-extraction
                - Inclusion/exclusion criteria for papers (scope: polymer classes, years)
                - Per-source license decision (include values only / exclude)
                - Search strings in config/search.yaml

LICENSE:        Code MIT; dataset CC BY 4.0 (author confirmation is part of release authorization). Records carry the
                source DOI and source license. No source text is redistributed: the release
                contains reported values and locators (section / table / figure), not snippets.

ASSUMPTIONS:    - First fetch attempt (2026-10-07) was blocked; the corpus was fetched on
                  2026-10-12. OpenAlex searches were tightened to quoted Boolean
                  title+abstract queries after an unquoted search returned 11,752 mostly
                  irrelevant works.
                - Pattern extraction (02_extract) proposes candidates only; release records come from
                  AI extraction files that pass source verification and blind re-extraction.
                - "Week 6" release date in the brief is a plan date, not a reason to wait.
```
