"""Shared helpers: paths, polite HTTP with backoff, provenance logging."""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
CURATED = ROOT / "data" / "curated"
PROCESSED = ROOT / "data" / "processed"
PAPER = ROOT / "paper"
PROVENANCE = RAW / "PROVENANCE.txt"

USER_AGENT = "PhotoDeg-Bench/1.0 (+https://github.com/; open research dataset build)"


def load_yaml(path: Path) -> dict:
    import yaml

    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def contact_email(cfg: dict) -> str:
    return os.environ.get("PHOTODEG_EMAIL") or (cfg.get("contact_email") or "")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def log_provenance(path: Path, url: str, note: str = "") -> None:
    """Append filename, bytes, SHA-256, URL, access date (same format as the skill's provenance.py)."""
    PROVENANCE.parent.mkdir(parents=True, exist_ok=True)
    rel = path.relative_to(RAW) if path.is_relative_to(RAW) else path.name
    line = " | ".join(
        [
            _dt.date.today().isoformat(),
            str(rel),
            f"{path.stat().st_size} bytes",
            f"sha256:{sha256_file(path)}",
            url,
            note,
        ]
    ).rstrip(" |")
    with open(PROVENANCE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def http_get(url: str, params: dict | None = None, email: str = "", max_tries: int = 6,
             min_interval: float = 0.25) -> bytes:
    """GET with exponential backoff on 429/5xx. Respects Retry-After."""
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    ua = USER_AGENT + (f" mailto:{email}" if email else "")
    delay = 2.0
    for attempt in range(1, max_tries + 1):
        req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "*/*"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            time.sleep(min_interval)
            return data
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise
            if e.code in (429, 500, 502, 503, 504) and attempt < max_tries:
                wait = float(e.headers.get("Retry-After") or delay)
                time.sleep(wait)
                delay *= 2
                continue
            raise
        except urllib.error.URLError:
            if attempt < max_tries:
                time.sleep(delay)
                delay *= 2
                continue
            raise
    raise RuntimeError(f"unreachable: {url}")


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def norm_doi(doi: str | None) -> str:
    if not doi:
        return ""
    d = doi.strip().lower()
    for p in ("https://doi.org/", "http://doi.org/", "doi:"):
        if d.startswith(p):
            d = d[len(p):]
    return d
