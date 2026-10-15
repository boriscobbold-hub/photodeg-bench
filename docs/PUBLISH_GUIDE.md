# Publish guide: PhotoDeg-Bench v1.0.0

Nothing has been published. The release candidate is built and the scientific checks pass (see [RELEASE_READINESS.md](RELEASE_READINESS.md)). Publication needs three things from the author, then about 30 minutes.

## 0. Author steps (gate items A1–A3)

1. Fill `AUTHORS.json`, then the same details in `CITATION.cff` (names, ORCID, repository URL), the copyright line in `LICENSE`, and the creators and repository URL in `docs/zenodo_metadata.json` (delete its `_comment` key).
2. Decide R08 and R14 in `rules/harmonization.yaml` (see `docs/VERIFY_CHECKLIST.md`). Add `endorsed_by: "<name>, <date>"` to each, after changing the decision if you want to.
3. Write `release/AUTHORIZATION.json` with `authorized_by`, `date`, `version: "1.0"` and a `statement` in your words.

Then run:

```bash
python tools/autonomous_release.py --target v1.0 --publish   # rebuilds, re-checks; refuses unless every S and A check passes
```

## 1. GitHub

A fine-grained token with Administration: write and Contents: write, held only in the shell:

```bash
export GITHUB_TOKEN=...
python tools/publish_github.py . --repo photodeg-bench --description "Source-verified benchmark of visible-light polymer deconstruction" --dry-run
python tools/publish_github.py . --repo photodeg-bench --description "Source-verified benchmark of visible-light polymer deconstruction"
```

The release-candidate history is on branch `dev/autonomous-v1`; merge it to `main` before pushing, or push the branch and open a PR.

## 2. Zenodo DOI (sandbox first)

**Path A (recommended), via the GitHub integration.** Log in to zenodo.org with ORCID → GitHub → enable `photodeg-bench` → create GitHub release `v1.0.0`. Then edit the Zenodo record from `docs/zenodo_metadata.json`.

**Path B, the script.**
```bash
python tools/autonomous_release.py --target v1.0          # rebuilds release/photodeg-bench-v1.0.0.zip
export ZENODO_SANDBOX_TOKEN=...                            # scopes deposit:write, deposit:actions
python tools/zenodo_deposit.py --files release/photodeg-bench-v1.0.0.zip --metadata docs/zenodo_metadata.json --sandbox --publish
# read the sandbox record as a stranger would, then:
export ZENODO_TOKEN=...
python tools/zenodo_deposit.py --files release/photodeg-bench-v1.0.0.zip --metadata docs/zenodo_metadata.json --publish
```

## 3. The same day

Put the DOI into `CITATION.cff` (`doi`, `date-released`) and the README status line. Add a row to `docs/evidence_log.csv` (date, artifact, dataset, Zenodo + GitHub, DOI, live, metrics snapshot, files saved, notes). Save PDFs of the Zenodo and GitHub release pages.

## AI-assistance disclosure

Already in the README, the methods, the Zenodo description and `AUTHORS.json`. Keep it unless it stops being true.
