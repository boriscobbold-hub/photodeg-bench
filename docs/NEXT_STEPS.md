# Next steps after v1.0

- **v1.1, close the access gap.** The 54 in-scope papers without retrievable full text (code E6 in `data/curated/screening_log.csv`) are the biggest gain available. They need publisher PDFs or HTML obtained legitimately: the author's library access, author-deposited versions, or a runner with publisher access. Add a PDF ingestion path (page-and-line locators) so the same verifier applies.
- **v1.1, human audit.** A domain expert (ideally SEC-experienced) checks a seeded random 10% of records plus all flagged records; agreement is reported in the QA report. This is the strongest addition to the dataset's credibility.
- **v1.1, figures and SI.** Values only in plots (time courses especially), with a recorded digitization tool and uncertainty, labelled `digitized`; supplementary tables.
- **v1.2, light dose.** Irradiance or photon flux where papers give enough to compute it, as a tier condition.
- **v1.2, scope extensions** pending the R08 decision: photothermal routes and photoreforming as separate, clearly labelled categories; mass-loss and mineralization endpoints as their own endpoint family.
- **Leaderboard page** with a GitHub issue template for submitting new records, verified by the same pipeline.
- **Data descriptor** from `docs/MANUSCRIPT_OUTLINE.md`.
- **Living updates:** quarterly `--refresh` runs; a new Zenodo version per release.
