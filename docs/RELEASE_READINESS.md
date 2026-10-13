# Release readiness: PhotoDeg-Bench v1.0

Generated 2026-10-12T21:07:00 by `tools/release_gate.py`. Regenerate; do not edit by hand.

**Scientific readiness: PASS.** **Release authorization: PENDING (author).**

| ID | Check | Status | Detail |
|---|---|---|---|
| S1 | test suite passes | pass | OK |
| S2 | schema and value validation: 0 errors | pass | 87 records, 0 errors, 2 warnings -> /home/claude/photodeg-bench/data/processed/validation_report.txt |
| S3 | QA report passes (no critical failures) | pass | RESULT: PASS  (0 critical, 0 warnings) |
| S4 | every released record source-verified and independently re-extracted | pass | 87 records; unverified: [] |
| S5 | no unresolved verification disagreements | pass | 0 unresolved |
| S6 | every required harmonization rule set and justified | pass | 15 rules |
| S7 | figures reproduce byte-for-byte from the final dataset | pass | all PNGs identical on regeneration |
| S8 | every source article has a provenance record (and matching hash when present) | pass | ok |
| S9 | every record's source license is allowed by rule R14 | pass | ok |
| S10 | no secrets or credentials in the repository | pass | none found |
| S11 | stats file agrees with the release table | pass | stats 87 vs table 87 |
| A1 | author metadata complete (AUTHORS.json, CITATION.cff, LICENSE, Zenodo metadata) | pending_author | placeholders remain |
| A2 | escalated scientific/legal rules endorsed by the author | pending_author | awaiting: ['R08_visible_window', 'R14_source_license_policy'] |
| A3 | public release authorized by the author | pending_author | release/AUTHORIZATION.json not present |
