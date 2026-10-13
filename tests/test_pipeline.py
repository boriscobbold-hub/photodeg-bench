"""Tests for PhotoDeg-Bench code paths. Run: python -m unittest discover -s tests -v

All inputs are synthetic fixtures in tests/fixtures/. They test that the code does what the
rules say; they say nothing about the chemistry.
"""

import csv
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
FIX = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(CODE))


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace(".py", "").lstrip("0123456789_"), CODE / name)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


extractors = load("extractors.py")
extract = load("02_extract.py")
validate = load("03_validate.py")
harm = load("04_harmonize.py")


def rows(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


class TestExtractors(unittest.TestCase):
    def test_molar_mass_pair_and_units(self):
        c = extractors.extract_all("the Mn decreased from 120 to 3.4 kg mol−1 after 24 h")
        mn = [x for x in c if x["field"] == "Mn"]
        self.assertEqual([x["value"] for x in mn], [120.0, 3.4])
        self.assertTrue(all(x["unit"] == "kg/mol" for x in mn))

    def test_dispersity_range(self):
        c = extractors.extract_all("dispersity changed from 2.1 to 1.6")
        self.assertEqual(sorted(x["value"] for x in c if x["field"] == "dispersity"), [1.6, 2.1])

    def test_abbreviation_case_sensitivity(self):
        c = extractors.extract_all("ps pe and pp are lowercase words here")
        self.assertFalse([x for x in c if x["field"] == "polymer"])
        c = extractors.extract_all("PS and Polystyrene")
        self.assertEqual(len([x for x in c if x["field"] == "polymer"]), 2)

    def test_styrene_not_inside_polystyrene(self):
        c = extractors.extract_all("polystyrene and poly(styrene) gave styrene monomer")
        prods = [x["value"] for x in c if x["field"] == "product" and x["value"] == "styrene"]
        self.assertEqual(len(prods), 1)

    def test_calibration_and_light(self):
        c = extractors.extract_all("SEC relative to polystyrene standards; 450 nm blue LEDs; 400-700 nm white LED")
        fields = {(x["field"], str(x["value"])) for x in c}
        self.assertIn(("sec_calibration", "conventional_PS"), fields)
        self.assertIn(("wavelength_nm", "450.0"), fields)
        self.assertIn(("wavelength_range_nm", "400-700"), fields)
        self.assertIn(("light_color", "blue"), fields)
        c = extractors.extract_all("Molar masses were determined by SEC in THF at 35 °C")
        self.assertIn(("sec_eluent", "THF"), {(x["field"], x["value"]) for x in c})

    def test_table_headers(self):
        cols = extractors.table_header_fields(["Entry", "Mn (kg mol−1)", "Đ", "λ (nm)", "Time (h)", "Mw × 10^-3"])
        self.assertEqual(cols[1], ("Mn", "kg/mol"))
        self.assertEqual(cols[2], ("dispersity", ""))
        self.assertEqual(cols[3], ("wavelength_nm", "nm"))
        self.assertEqual(cols[4], ("time", "h"))
        self.assertIn("header scale", cols[5][1])

    def test_jats_fixture(self):
        c = extract.extract_file(FIX / "synthetic_article.xml", "SYN")
        tbl = [x for x in c if x["source"] == "table" and x["field"] == "Mn"]
        self.assertEqual(sorted(x["value"] for x in tbl), [3.4, 15.2, 118.0])
        self.assertTrue(all(x["locator"].startswith("Table 1 r") for x in tbl))


class TestValidate(unittest.TestCase):
    def test_fixture_is_clean(self):
        errors, warnings = validate.validate(rows(FIX / "synthetic_records.csv"), [])
        self.assertEqual(errors, [])

    def test_catches_errors(self):
        r = rows(FIX / "synthetic_records.csv")[0]
        bad = dict(r, record_id="X", mn_before="-1", disp_after="0.9", source_verified="",
                   mass_unit_after="kg", wavelength_nm="1200", doi="doi:abc")
        errors, _ = validate.validate([bad], [])
        text = "\n".join(errors)
        for needle in ("mn_before must be > 0", "disp_after", "source_verified", "mass_unit_after",
                       "wavelength_nm=1200", "bare DOI"):
            self.assertIn(needle, text)

    def test_warns_on_increase(self):
        r = rows(FIX / "synthetic_records.csv")[0]
        _, warnings = validate.validate([dict(r, mn_after="200")], [])
        self.assertTrue(any("mn_after > mn_before" in w for w in warnings))


class TestHarmonize(unittest.TestCase):
    def setUp(self):
        import yaml
        self.rules = yaml.safe_load((FIX / "synthetic_rules.yaml").read_text())
        self.out, self.log = harm.harmonize(rows(FIX / "synthetic_records.csv"), self.rules)
        self.by = {h["record_id"]: h for h in self.out}

    def test_refuses_unset_rules(self):
        import copy
        r = copy.deepcopy(self.rules)
        r["rules"]["R02_primary_average"]["status"] = "unset"
        with self.assertRaises(SystemExit):
            harm.check_rules(r)

    def test_license_gate(self):
        self.assertNotIn("SYN-004", self.by)
        self.assertTrue(any(l["record_id"] == "SYN-004" and l["rule"] == "R14" for l in self.log))

    def test_metrics(self):
        h = self.by["SYN-001"]
        self.assertAlmostEqual(h["retained_fraction"], 3.4 / 120)
        self.assertAlmostEqual(h["scissions_per_chain"], 120 / 3.4 - 1)
        self.assertEqual(h["tier_product_yield"], "P1")
        self.assertEqual(h["thermal_regime"], "ambient")
        self.assertEqual(h["primary_average"], "Mn")
        self.assertEqual(h["calibration_class"], "matched_conventional")
        self.assertEqual(h["wavelength_band"], "band_hi")
        self.assertEqual(h["tier_molar_mass"], "T1")

    def test_unit_and_time_conversion(self):
        h = self.by["SYN-003"]
        self.assertAlmostEqual(h["mn_before_h"], 50.0)
        self.assertAlmostEqual(h["time_h"], 1.5)
        self.assertEqual(h["calibration_class"], "mismatched_conventional")
        self.assertEqual(h["mass_basis"], "universal_conversion")
        self.assertEqual(h["tier_molar_mass"], "T2")

    def test_control_flag(self):
        self.assertEqual(self.by["SYN-002"]["is_control"], "y")

    def test_universal_calibration_formula(self):
        table = [{"polymer": "A", "eluent": "THF", "temperature_c": 35, "K": 0.0114, "a": 0.716},
                 {"polymer": "B", "eluent": "THF", "temperature_c": 35, "K": 0.0128, "a": 0.69}]
        got = harm.universal_convert(1e5, "A", "B", "THF", 35, table)
        expected = ((0.0114 / 0.0128) * 1e5 ** 1.716) ** (1 / 1.69)
        self.assertAlmostEqual(got, expected, places=6)
        # [eta]*M must be equal for the two polymers at the converted mass
        self.assertAlmostEqual(0.0114 * 1e5 ** 1.716, 0.0128 * got ** 1.69, delta=1e-6 * 0.0114 * 1e5 ** 1.716)


class TestFetchMerge(unittest.TestCase):
    """Offline test of corpus merging and screening with hand-written API-shaped payloads."""

    def test_merge_dedupes_on_doi_and_screens(self):
        fetch = load("01_fetch.py")
        cfg = {"year_min": 2010, "screening": {"light_terms": ["visible"], "polymer_terms": ["polystyrene"],
                                                "outcome_terms": ["degradation"]}}
        epmc = {"10.1/a": {"epmc": {"doi": "10.1/A", "pmcid": "PMC1", "title": "Visible light degradation of polystyrene",
                                     "pubYear": "2021", "license": "CC BY", "isOpenAccess": "Y"}, "queries": {"epmc0"}}}
        oa = {"10.1/a": {"oa": {"id": "https://openalex.org/W1", "doi": "https://doi.org/10.1/a", "title": "x",
                                "publication_year": 2021, "ids": {}, "best_oa_location": {"license": "cc-by"},
                                "open_access": {"oa_status": "gold"}}, "queries": {"oa0"}},
              "10.1/b": {"oa": {"id": "https://openalex.org/W2", "doi": "https://doi.org/10.1/b", "title": "Unrelated",
                                "publication_year": 2005, "ids": {"pmcid": "https://www.ncbi.nlm.nih.gov/pmc/articles/123"},
                                "abstract_inverted_index": {"hello": [0]}}, "queries": {"oa1"}}}
        rows = {r["paper_id"]: r for r in fetch.merge(epmc, oa, cfg)}
        self.assertEqual(len(rows), 2)
        a = rows["10.1/a"]
        self.assertEqual((a["pmcid"], a["auto_screen"], a["found_by"]), ("PMC1", "pass", "epmc0;oa0"))
        b = rows["10.1/b"]
        self.assertEqual((b["pmcid"], b["in_year_scope"], b["auto_screen"]), ("PMC123", "n", "fail"))


class TestEndToEnd(unittest.TestCase):
    def test_cli_chain(self):
        with tempfile.TemporaryDirectory() as td:
            subprocess.run([sys.executable, str(CODE / "03_validate.py"), "--records", str(FIX / "synthetic_records.csv"),
                            "--screening", "/nonexistent", "--report", f"{td}/v.txt"], check=True)
            subprocess.run([sys.executable, str(CODE / "04_harmonize.py"), "--rules", str(FIX / "synthetic_rules.yaml"),
                            "--records", str(FIX / "synthetic_records.csv"), "--out-dir", td, "--version", "test"], check=True)
            out = rows(Path(td) / "photodeg_bench_vtest.csv")
            self.assertEqual(len(out), 3)


if __name__ == "__main__":
    unittest.main()
