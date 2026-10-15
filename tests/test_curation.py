"""Regression tests for the autonomous-curation components (synthetic fixtures only)."""
import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(ROOT / "code" / "curation"))
sys.path.insert(0, str(ROOT / "tools"))


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


VR = load(ROOT / "code/curation/verify_records.py", "verify_records")
CB = load(ROOT / "code/curation/compare_blind.py", "compare_blind")
HZ = load(ROOT / "code/04_harmonize.py", "harmonize")


def fixture_blocks():
    out = {}
    for loc, kind, payload in VR.X.parse_jats(FIX / "synthetic_nested_table.xml"):
        if kind == "text":
            out[VR.norm(loc)] = payload
        else:
            header, rows = payload
            base = VR.norm(loc)
            for j, h in enumerate(header):
                out[f"{base} h c{j + 1}"] = h
            for i, r in enumerate(rows):
                for j, c in enumerate(r):
                    out[f"{base} r{i + 1} c{j + 1}"] = c
    return out


class TestParser(unittest.TestCase):
    def test_nested_table_is_separate_and_headers_expand(self):
        items = list(VR.X.parse_jats(FIX / "synthetic_nested_table.xml"))
        tables = [p for loc, k, p in items if k == "table"]
        self.assertEqual(len(tables), 1)
        header, rows = tables[0]
        self.assertEqual(header, ["Polymer", "Mn (g.mol-1) Before", "Mn (g.mol-1) After"])
        self.assertEqual(rows[0], ["P-1", "67,000", "53,000"])
        para = [p for loc, k, p in items if k == "text" and loc.startswith("Results")][0]
        self.assertNotIn("67,000", para)          # cells no longer run into the paragraph text
        self.assertIn("The values decreased", para)


class TestVerifier(unittest.TestCase):
    def setUp(self):
        self._orig = VR.blocks
        B = fixture_blocks()
        VR.blocks = lambda pmcid: B

    def tearDown(self):
        VR.blocks = self._orig

    def test_numbers(self):
        self.assertIn(67000.0, VR.numbers_in("67,000"))
        self.assertIn(1.4, VR.numbers_in("1,4"))
        self.assertIn(0.065, VR.numbers_in("0,065"))
        self.assertNotIn(65.0, VR.numbers_in("0,065"))
        self.assertIn(260000.0, VR.numbers_in("Mw ∼ 260 000"))
        self.assertIn(3.0, VR.numbers_in("in triplicate"))

    def test_outcomes(self):
        ok = VR.check_field("X", "mn_before", {"v": 67000, "loc": "Table 1. r1 c2", "s": "67,000"})
        self.assertEqual(ok[0], "matched")
        wrong_value = VR.check_field("X", "mn_before", {"v": 76000, "loc": "Table 1. r1 c2", "s": "67,000"})
        self.assertEqual(wrong_value[0], "mismatch")
        wrong_cell = VR.check_field("X", "mn_after", {"v": 53000, "loc": "Table 1. r1 c2", "s": "53,000"})
        self.assertEqual(wrong_cell[0], "string_missing")
        no_loc = VR.check_field("X", "mn_after", {"v": 53000, "loc": "Table 9 r1 c1", "s": "53,000"})
        self.assertEqual(no_loc[0], "locator_missing")
        inferred_ok = VR.check_field("X", "mass_unit_after", {"v": "g/mol", "inferred": "printed in header"})
        self.assertEqual(inferred_ok[0], "inferred")
        inferred_bad = VR.check_field("X", "mn_after", {"v": 53000, "inferred": "guess"})
        self.assertEqual(inferred_bad[0], "mismatch")
        reps = VR.check_field("X", "replicates", {"v": 3, "loc": "Table 1. footnote", "s": "in triplicate"})
        self.assertEqual(reps[0], "matched")


class TestBlindCompare(unittest.TestCase):
    def test_same(self):
        self.assertTrue(CB.same(20, "20.0"))
        self.assertTrue(CB.same(0.065, 0.0651))
        self.assertFalse(CB.same(70, 90))
        self.assertTrue(CB.same("THF", "thf"))
        self.assertFalse(CB.same("THF", "chloroform"))


class TestRulesAndGate(unittest.TestCase):
    def test_harmonizer_refuses_any_unset_rule(self):
        import yaml
        rules = yaml.safe_load((ROOT / "rules/harmonization.yaml").read_text())
        HZ.check_rules(rules)  # the shipped rules are all set
        broken = copy.deepcopy(rules)
        broken["rules"]["R01_canonical_mass_unit"]["status"] = "unset"
        with self.assertRaises(SystemExit):
            HZ.check_rules(broken)

    def test_author_checks_pending_without_authorization(self):
        G = load(ROOT / "tools/release_gate.py", "release_gate")
        checks = {c["id"]: c for c in G.author_checks()}
        if not (ROOT / "release/AUTHORIZATION.json").exists():
            self.assertEqual(checks["A3"]["status"], "pending_author")
        self.assertTrue(all(c["kind"] == "author" for c in checks.values()))


class TestValidatorReleaseCriteria(unittest.TestCase):
    def test_requires_both_verifications(self):
        V = load(ROOT / "code/03_validate.py", "validate")
        import csv
        r = list(csv.DictReader(open(FIX / "synthetic_records.csv")))[0]
        errs, _ = V.validate([dict(r, blind_verified="n")], [])
        self.assertTrue(any("blind_verified" in e for e in errs))
        errs, _ = V.validate([dict(r, mn_before="", mn_after="", product_yields="")], [])
        self.assertTrue(any("no benchmark endpoint" in e for e in errs))


if __name__ == "__main__":
    unittest.main()
