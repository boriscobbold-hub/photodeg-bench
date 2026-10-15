#!/usr/bin/env python3
"""AI stages for unattended runs: full-text screening + extraction (Agent C) and blind re-extraction (Agent D).

  python code/curation/llm_runner.py --pending          # process every paper that still needs an AI stage
  python code/curation/llm_runner.py --extract PMCxxxx  # one paper
  python code/curation/llm_runner.py --blind PMCxxxx    # blind re-extraction for one paper (needs slots)

Status: written in the v1.0 build session but NOT exercised there (no API key in that environment; the AI
stages for v1.0 were run in-session with the same protocol). Treat the first unattended run as a test:
compare its output on one already-curated paper against the committed files before trusting it.

Design: the model never writes release data directly. Extraction output must pass verify_records.py
(re-prompted with the verifier's errors up to max_repair_rounds, then the paper is left pending with its
errors logged). Blind output only feeds compare_blind.py; disagreements go to the adjudication queue,
which blocks release until resolved.

Usage and estimated cost per call are appended to data/work/api_usage.jsonl.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
EX = ROOT / "data/curated/extractions"
BLIND = ROOT / "data/curated/verification/blind"
SLOTS = ROOT / "data/curated/verification/slots"
USAGE = ROOT / "data/work/api_usage.jsonl"
CFG = yaml.safe_load((ROOT / "config/llm.yaml").read_text())
PY = sys.executable
_last_call = [0.0]


def call(model, system, user):
    key = os.environ.get(CFG["api_key_env"])
    if not key:
        raise RuntimeError("no API key")
    wait = CFG["min_seconds_between_calls"] - (time.time() - _last_call[0])
    if wait > 0:
        time.sleep(wait)
    body = json.dumps({"model": model, "max_tokens": CFG["max_tokens"], "system": system,
                       "messages": [{"role": "user", "content": user}]}).encode()
    for attempt in range(1, CFG["max_retries"] + 1):
        req = urllib.request.Request(CFG["base_url"].rstrip("/") + "/v1/messages", data=body, method="POST",
                                     headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                d = json.loads(r.read())
            _last_call[0] = time.time()
            u = d.get("usage", {})
            price = (CFG.get("price_per_mtok") or {}).get(model) or {}
            cost = None
            if price.get("input") is not None and price.get("output") is not None:
                cost = (u.get("input_tokens", 0) * price["input"] + u.get("output_tokens", 0) * price["output"]) / 1e6
            USAGE.parent.mkdir(parents=True, exist_ok=True)
            with open(USAGE, "a") as f:
                f.write(json.dumps({"time": dt.datetime.now().isoformat(timespec="seconds"), "model": model,
                                    "input_tokens": u.get("input_tokens"), "output_tokens": u.get("output_tokens"), "usd_estimate": cost}) + "\n")
            return "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text")
        except Exception as e:  # noqa: BLE001
            if attempt == CFG["max_retries"]:
                raise
            time.sleep(10 * attempt)


def pack(pmcid):
    r = subprocess.run([PY, "code/curation/evidence_pack.py", pmcid, "--all", "--max-chars", "6000"], cwd=ROOT, capture_output=True, text=True)
    return r.stdout


def json_from(text):
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON in model output")
    return json.loads(m.group(0))


def extract(pmcid, doi, license_):
    system = ("You are Agent C, an extraction curator for PhotoDeg-Bench. Follow the eligibility criteria and the extraction "
              "protocol exactly. Never infer a number; every value needs the exact locator and literal source string from the "
              "evidence pack. Output one JSON object only.")
    docs = (ROOT / "docs/ELIGIBILITY.md").read_text() + "\n\n" + (ROOT / "docs/EXTRACTION_PROTOCOL.md").read_text()
    ex1 = (EX / "PMC9586668.json").read_text()
    ex2 = (EX / "PMC9295126.json").read_text()
    user = (f"{docs}\n\nWORKED EXAMPLE 1:\n{ex1}\n\nWORKED EXAMPLE 2:\n{ex2}\n\nPAPER: {pmcid} | DOI {doi} | license {license_}\n"
            f"EVIDENCE PACK:\n{pack(pmcid)}\n\nWrite the extraction JSON for this paper (include or exclude, with records if included).")
    out = EX / f"{pmcid}.json"
    for rnd in range(CFG["max_repair_rounds"] + 1):
        d = json_from(call(CFG["model_extraction"], system, user))
        d.update({"paper_key": pmcid, "pmcid": pmcid, "doi": doi, "paper_id": doi, "source_license": license_,
                  "extractor": f"{CFG['model_extraction']} via llm_runner, {dt.date.today().isoformat()}"})
        out.write_text(json.dumps(d, indent=1, ensure_ascii=False))
        r = subprocess.run([PY, "code/curation/verify_records.py", "--paper", pmcid], cwd=ROOT, capture_output=True, text=True)
        problems = [l for l in r.stdout.splitlines() if l.startswith("  ")]
        if not problems:
            return True
        user += f"\n\nYOUR PREVIOUS OUTPUT FAILED VERIFICATION:\n" + "\n".join(problems[:60]) + "\nFix the locators/strings/values against the evidence pack (or drop the field and list it in excluded_observations) and output the full corrected JSON."
    d = json.loads(out.read_text())
    d["screen"]["decision"] = "pending_verification"
    out.write_text(json.dumps(d, indent=1, ensure_ascii=False))
    return False


def blind(pmcid):
    slots = json.loads((SLOTS / f"{pmcid}.json").read_text())
    system = ("You are Agent D, an independent verifier. You have NOT seen any other curator's values. Read the evidence pack and "
              "report, for each task, the values the article gives for that record, with locator and literal source string; null when "
              "the article does not attach a value to that record. Raise concerns. Output one JSON object only.")
    user = ((ROOT / "docs/EXTRACTION_PROTOCOL.md").read_text() + f"\n\nSLOTS:\n{json.dumps(slots, indent=1)}\n\nEVIDENCE PACK:\n{pack(pmcid)}\n\n"
            'Output: {"pmcid":..., "verifier":..., "tasks":[{"rid":..., "values":{field:{"v","loc","s"}|null}, "yields":{product:{"v","u","loc","s"}|null}, "concerns":[...]}], "paper_concerns":[...]}')
    d = json_from(call(CFG["model_verification"], system, user))
    d["verifier"] = f"{CFG['model_verification']} via llm_runner, {dt.date.today().isoformat()}"
    BLIND.mkdir(parents=True, exist_ok=True)
    (BLIND / f"{pmcid}.json").write_text(json.dumps(d, indent=1, ensure_ascii=False))


def pending():
    log = list(csv.DictReader(open(ROOT / "data/curated/screening_log.csv", encoding="utf-8")))
    scr = {r["paper_id"]: r for r in csv.DictReader(open(ROOT / "data/curated/screening.csv", encoding="utf-8"))}
    need_x = [scr[l["paper_id"]] for l in log if l["code"] == "pending_fulltext" and scr[l["paper_id"]]["pmcid"]
              and not (EX / f"{scr[l['paper_id']]['pmcid']}.json").exists()]
    need_b = []
    for f in EX.glob("*.json"):
        d = json.loads(f.read_text())
        if d["screen"]["decision"] == "include" and not any(BLIND.glob(f"{d['pmcid']}*.json")):
            need_b.append(d["pmcid"])
    return need_x, need_b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pending", action="store_true")
    ap.add_argument("--extract")
    ap.add_argument("--blind")
    a = ap.parse_args()
    have_key = bool(os.environ.get(CFG["api_key_env"]))
    if a.pending:
        need_x, need_b = pending()
        print(f"pending extraction: {[p['pmcid'] for p in need_x]}; pending blind verification: {need_b}")
        if not have_key:
            print(f"{CFG['api_key_env']} not set: AI stages skipped. Pending papers are not released (fail-safe).")
            return 0
        for p in need_x:
            print(p["pmcid"], "extract ->", extract(p["pmcid"], p["doi"], p["license"]))
        subprocess.run([PY, "code/curation/blind_slots.py"], cwd=ROOT)
        for pm in pending()[1]:
            blind(pm); print(pm, "blind done")
        return 0
    if not have_key:
        sys.exit(f"{CFG['api_key_env']} not set")
    if a.extract:
        row = next(r for r in csv.DictReader(open(ROOT / "data/curated/screening.csv", encoding="utf-8")) if r["pmcid"] == a.extract)
        print(extract(a.extract, row["doi"], row["license"]))
    if a.blind:
        subprocess.run([PY, "code/curation/blind_slots.py"], cwd=ROOT)
        blind(a.blind)
    return 0


if __name__ == "__main__":
    sys.exit(main())
