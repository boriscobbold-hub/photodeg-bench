# Publish guide: PhotoDeg-Bench v1.0.0

> DRAFT. Nothing has been pushed or deposited yet: this session had no GitHub or Zenodo token and could not reach either service. Every step below is for the curator to run after the verification checklist is complete. Budget: about 45 minutes.

## 0. Gate (5 min)

```bash
python code/06_figures.py --final        # removes the stamp from figures
# delete the status banner (first line) of README.md and docs/*.md; fill every verify-tagged field
python tools/publish_gate.py .           # must pass; fix whatever it lists
```

The gate blocks on any draft stamp, verify tag, bracketed placeholder or secret, anywhere in the repository except the paths in `.gate-allow` (the gate's own code and the figure script, which contain those strings by design). `publish_github.py` runs the same gate and stops if it fails.

## 1. GitHub (10 min)

Create a fine-grained token at github.com → Settings → Developer settings → Fine-grained tokens, with **Administration: write** and **Contents: write** on your account. Then, in a terminal (never in a file):

```bash
export GITHUB_TOKEN=...                  # paste; not saved anywhere
python tools/publish_github.py . --repo photodeg-bench \
  --description "Open, harmonized benchmark of visible-light polymer deconstruction" \
  --release v1.0.0 --dry-run             # look at what it will do
python tools/publish_github.py . --repo photodeg-bench \
  --description "Open, harmonized benchmark of visible-light polymer deconstruction"
```

Don't tag the release yet if you want Zenodo to mint the DOI from the GitHub release (path 2a).

## 2. Zenodo DOI (15 min). Choose one path.

**2a. GitHub integration (recommended; future versions get DOIs automatically).**
1. Log in at zenodo.org with ORCID.
2. Profile menu → GitHub → flip the switch for `photodeg-bench`.
3. On GitHub, create release `v1.0.0` (Releases → Draft a new release → tag `v1.0.0`, title "PhotoDeg-Bench v1.0.0", notes: one paragraph + link to LIMITATIONS).
4. Within minutes Zenodo shows the record with a DOI. Open it, click Edit, and fix creators/ORCID, license (CC BY 4.0), keywords, and description from `docs/zenodo_metadata.json`. Save and publish.

**2b. Direct deposit with the script (sandbox first).**
1. Tokens: sandbox.zenodo.org and zenodo.org → Applications → Personal access tokens, scopes `deposit:write` and `deposit:actions`.
2. Build the archive: `git archive --format=zip -o release/photodeg-bench-v1.0.0.zip v1.0.0`
3. Sandbox:
   ```bash
   export ZENODO_SANDBOX_TOKEN=...
   python tools/zenodo_deposit.py --files release/photodeg-bench-v1.0.0.zip data/processed/photodeg_bench_v1.0.csv docs/CODEBOOK.md \
     --metadata docs/zenodo_metadata.json --sandbox --publish
   ```
   Open the sandbox record and read it as a stranger would.
4. Real: same command with `ZENODO_TOKEN` and without `--sandbox`. Copy the DOI it prints.

## 3. Same day (10 min)

1. Put the DOI in `CITATION.cff` (`doi:` and `date-released:`), the README status line, and a DOI badge at the top of the README; commit and push.
2. Add a row to `docs/evidence_log.csv`: date, "PhotoDeg-Bench v1.0.0 release", dataset, "Zenodo + GitHub", DOI, live, metrics snapshot (0 downloads), files saved (PDF prints of the Zenodo and GitHub release pages), notes ("verification checklist completed YYYY-MM-DD").
3. Save PDFs of the Zenodo record and GitHub release page next to the log.

## AI-assistance disclosure

Zenodo has no required field. Suggested sentence for the README and Zenodo description, kept only if true: "Extraction and validation code was written with AI assistance (Claude); all harmonization rules were set, and every record entered or checked against its source, by the curator."
