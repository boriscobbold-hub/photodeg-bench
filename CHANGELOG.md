# Changelog

## v1.0.0 release candidate (2026-10-12)
- Corpus: Europe PMC + OpenAlex open-access search (fetched 2026-10-12); OpenAlex queries tightened to quoted Boolean title-and-abstract searches.
- Autonomous AI curation workflow (screening, extraction, deterministic verification, blind re-extraction, adjudication, harmonization, QA), replacing the curator-only design of the 0.x scaffold. Curation method and its guarantees: docs/METHODS_AUTOMATED_CURATION.md.
- Parser: tables nested in paragraphs are emitted as tables; colspan/rowspan headers are expanded.
- Schema: control flag, replicates, yield uncertainty, extraction method, source_verified, blind_verified, QA flags; `checked_against_source` replaced by `source_verified` and `blind_verified`.
- Harmonization rules R01–R15 set (R15 thermal regime new); separate tiers for molar-mass and product-yield endpoints; scissions per chain dropped.
- Release gate split into scientific readiness (machine) and release authorization (author).
- Orchestrator `tools/autonomous_release.py` with checkpoints, resumable stages and progress reporting.

## v0.1 (2026-10-07)
- Pipeline scaffold: fetch, pattern extraction, validation, rule-driven harmonization, QA, figures, documentation.
