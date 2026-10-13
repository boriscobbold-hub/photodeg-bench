#!/usr/bin/env python3
"""Master orchestration for PhotoDeg-Bench: fetch -> screen -> extract -> verify -> harmonize -> QA ->
figures -> release candidate -> (only with the author's authorization) publish.

  python tools/autonomous_release.py --target v1.0              # resume from checkpoints, build release candidate
  python tools/autonomous_release.py --target v1.0 --refresh    # also re-fetch the corpus
  python tools/autonomous_release.py --target v1.0 --status     # print progress and exit
  python tools/autonomous_release.py --target v1.0 --publish    # publish (refused without release/AUTHORIZATION.json)

State and progress: data/work/state.json (checkpoints: per stage, input hashes, outputs, status) and
data/work/progress.json (machine-readable summary). Logs: data/work/logs/<stage>.log. API usage and cost:
data/work/api_usage.jsonl (written by code/curation/llm_runner.py).

AI stages (screening of new full texts, extraction, blind verification) need a model. In the build
session they were run by Claude in-session and their outputs are the files in data/curated/extractions/
and data/curated/verification/blind/. On a persistent runner, set ANTHROPIC_API_KEY and the orchestrator
calls llm_runner.py for any included-candidate paper that has no extraction or no blind file yet. Without a
key, pending papers are reported and the run continues with what is verified (fail-safe: nothing
unverified is released).

Stages are skipped when their inputs are unchanged since the last successful run (sha256 of inputs).
Each stage has bounded retries. A failed critical stage stops the run with a non-zero exit code and
leaves every completed output in place.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "data/work"
STATE = WORK / "state.json"
PROGRESS = WORK / "progress.json"
LOGS = WORK / "logs"
PY = sys.executable


def h_files(paths):
    h = hashlib.sha256()
    for p in paths:
        p = ROOT / p
        files = sorted(p.rglob("*")) if p.is_dir() else [p]
        for f in files:
            if f.is_file() and "__pycache__" not in f.parts:
                h.update(str(f.relative_to(ROOT)).encode())
                h.update(f.read_bytes())
    return h.hexdigest()


# name, command, inputs (for change detection), critical, retries
STAGES = [
    ("fetch", [PY, "code/01_fetch.py"], ["config/search.yaml"], True, 2),
    ("candidates", [PY, "code/02_extract.py", "--all-screened"], ["data/curated/screening.csv", "code/02_extract.py", "code/extractors.py"], False, 1),
    ("triage", [PY, "code/02b_triage.py"], ["data/processed/candidates.jsonl", "code/02b_triage.py"], False, 1),
    ("screen", [PY, "code/curation/screen_decisions.py"], ["code/curation/screen_decisions.py", "data/curated/extractions", "data/work/abstracts.json"], True, 1),
    ("ai_stages", [PY, "code/curation/llm_runner.py", "--pending"], ["data/curated/screening_log.csv", "data/curated/extractions", "data/curated/verification/blind"], False, 1),
    ("verify_deterministic", [PY, "code/curation/verify_records.py"], ["data/curated/extractions", "code/curation/verify_records.py", "code/02_extract.py"], True, 1),
    ("verify_blind_compare", [PY, "code/curation/compare_blind.py"], ["data/curated/extractions", "data/curated/verification/blind", "code/curation/compare_blind.py"], True, 1),
    ("adjudications", [PY, "code/curation/apply_adjudications.py"], ["code/curation/apply_adjudications.py"], True, 1),
    ("verify_after_adjudication", [PY, "code/curation/verify_records.py"], ["data/curated/extractions"], True, 1),
    ("compare_after_adjudication", [PY, "code/curation/compare_blind.py"], ["data/curated/extractions", "data/curated/verification/blind"], True, 1),
    ("build_records", [PY, "code/curation/build_records.py"], ["data/curated/extractions", "data/curated/verification", "code/curation/build_records.py"], True, 1),
    ("screen_final", [PY, "code/curation/screen_decisions.py"], ["data/curated/extractions"], True, 1),
    ("licenses", [PY, "code/curation/check_licenses.py"], ["data/curated/extractions"], False, 2),
    ("validate", [PY, "code/03_validate.py"], ["data/curated/records.csv", "code/03_validate.py"], True, 1),
    ("harmonize", [PY, "code/04_harmonize.py", "--version", "1.0"], ["data/curated/records.csv", "rules/harmonization.yaml", "code/04_harmonize.py"], True, 1),
    ("qa", [PY, "code/05_qa.py", "--version", "1.0"], ["data/processed", "data/curated", "code/05_qa.py"], True, 1),
    ("figures", None, ["data/processed/photodeg_bench_v1.0.csv", "paper/stats.json", "code/06_figures.py"], True, 1),
    ("docs", [PY, "tools/build_docs.py"], ["paper/stats.json", "docs/templates"], True, 1),
    ("readiness", [PY, "tools/release_gate.py", "--mode", "readiness"], [], True, 1),
    ("package", [PY, "tools/build_release.py", "--version", "1.0"], [], True, 1),
]


def load_state():
    return json.loads(STATE.read_text()) if STATE.exists() else {"stages": {}}


def save(state, extra=None):
    WORK.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=1))
    prog = {"updated": dt.datetime.now().isoformat(timespec="seconds"),
            "stages": {k: v.get("status") for k, v in state["stages"].items()}}
    if (ROOT / "release/READINESS.json").exists():
        r = json.loads((ROOT / "release/READINESS.json").read_text())
        prog.update({"scientifically_ready": r["scientifically_ready"], "release_authorized": r["release_authorized"]})
    if (ROOT / "paper/stats.json").exists():
        s = json.loads((ROOT / "paper/stats.json").read_text())
        prog.update({k: s.get(k) for k in ("n_included_papers", "n_records_released", "n_unresolved", "n_in_scope_no_fulltext")})
    if extra:
        prog.update(extra)
    PROGRESS.write_text(json.dumps(prog, indent=1))


def run_stage(name, cmd, retries):
    LOGS.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, retries + 1):
        t0 = time.time()
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        (LOGS / f"{name}.log").write_text(f"$ {' '.join(cmd)}\n# attempt {attempt}, exit {r.returncode}, {time.time() - t0:.1f}s\n\n{r.stdout}\n{r.stderr}")
        if r.returncode == 0:
            return True, r
        time.sleep(min(30, 5 * attempt))
    return False, r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="v1.0")
    ap.add_argument("--refresh", action="store_true", help="re-run the corpus fetch")
    ap.add_argument("--force", action="store_true", help="re-run every stage regardless of checkpoints")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--publish", action="store_true")
    a = ap.parse_args()
    if a.target != "v1.0":
        sys.exit("only --target v1.0 is defined")
    state = load_state()
    if a.status:
        print(PROGRESS.read_text() if PROGRESS.exists() else "no progress yet")
        return 0

    for name, cmd, inputs, critical, retries in STAGES:
        st = state["stages"].get(name, {})
        if name == "fetch" and not a.refresh and (ROOT / "data/processed/corpus.csv").exists():
            state["stages"][name] = {**st, "status": "skipped (corpus present; use --refresh)"}
            save(state); continue
        if name == "candidates" and not (ROOT / "data/raw/fulltext").exists():
            state["stages"][name] = {**st, "status": "skipped (no full texts; run --refresh)"}
            save(state); continue
        if name == "figures":
            ready = False
            # figures are final only once every scientific check except figure reproduction already passes
            r = subprocess.run([PY, "tools/release_gate.py", "--mode", "readiness"], cwd=ROOT, capture_output=True, text=True)
            rep = json.loads((ROOT / "release/READINESS.json").read_text())
            ready = all(c["status"] == "pass" for c in rep["checks"] if c["kind"] == "science" and c["id"] != "S7")
            (ROOT / "release").mkdir(exist_ok=True)
            marker = ROOT / "release/.figures_final"
            if ready:
                marker.write_text("final figures: scientific checks S1-S6, S8-S11 passed\n")
            elif marker.exists():
                marker.unlink()
            cmd = [PY, "code/06_figures.py", "--version", "1.0"] + (["--final"] if ready else [])
        digest = h_files(inputs) if inputs else None
        if not a.force and digest and st.get("status") == "ok" and st.get("inputs_sha256") == digest:
            state["stages"][name]["status_note"] = "unchanged inputs; skipped"
            save(state); continue
        print(f"[{name}] running")
        ok, r = run_stage(name, cmd, retries)
        state["stages"][name] = {"status": "ok" if ok else "failed", "inputs_sha256": digest,
                                 "finished": dt.datetime.now().isoformat(timespec="seconds"),
                                 "log": f"data/work/logs/{name}.log", "tail": (r.stdout or r.stderr)[-400:]}
        save(state)
        if not ok and critical:
            print(f"[{name}] FAILED (critical). See data/work/logs/{name}.log. Completed outputs are preserved.")
            return 1
        if not ok:
            print(f"[{name}] failed (non-critical); continuing")

    if a.publish:
        r = subprocess.run([PY, "tools/release_gate.py", "--mode", "publish"], cwd=ROOT, capture_output=True, text=True)
        print(r.stdout[-1500:])
        if r.returncode != 0:
            print("Publication not performed. Scientific readiness and the author's authorization are both required.")
            return 1
        print("Gate passed. Publication commands are listed in docs/PUBLISH_GUIDE.md; run them with your credentials.")
    rep = json.loads((ROOT / "release/READINESS.json").read_text())
    print(f"\nscientifically ready: {rep['scientifically_ready']}   release authorized: {rep['release_authorized']}")
    print("details: docs/RELEASE_READINESS.md; progress: data/work/progress.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
