"""Self-check for seo_scorer env config and link classification. Run: python3 test_scorer.py"""
import importlib
import os
import tempfile
import unittest
from pathlib import Path


def load(**env):
    """Import seo_scorer fresh, because its config constants are read at import time."""
    for key in ("SCORE_THRESHOLD", "LOCAL_CURRENCY", "LOCAL_AUTHORITIES", "LINKING_MAP"):
        os.environ.pop(key, None)
    os.environ.update(env)
    return importlib.reload(importlib.import_module("seo_scorer"))


ARTICLE = "# Title\n\n" + ("The price rose 12% in 2024. " * 200)


class ScorerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_threshold_from_env_controls_passed(self):
        self.assertTrue(load(SCORE_THRESHOLD="0").score_content(ARTICLE)["passed"])
        self.assertFalse(load(SCORE_THRESHOLD="101").score_content(ARTICLE)["passed"])

    def test_mapped_sibling_link_counts_as_internal(self):
        mapfile = Path(self.tmp.name) / "map.md"
        mapfile.write_text("- [pricing](https://www.sibling.example/pricing)\n- sibling.example - pricing pages\n")
        m = load(LINKING_MAP=str(mapfile))
        self.assertTrue(m.is_internal_url("https://www.sibling.example/rent"))
        self.assertFalse(m.is_internal_url("https://other.example/rent"))
        md = "[a](https://sibling.example/x) [b](https://other.example/y) [c](/local)"
        self.assertEqual(m.score_seo(md)["details"]["internal_links"], 2)
        self.assertEqual(m.score_seo(md)["details"]["external_links"], 1)
        html = '<a href="https://sibling.example/x">a</a><a href="https://other.example/y">b</a>'
        parsed = m.parse_html(html)
        self.assertEqual((parsed["internal_links"], parsed["external_links"]), (1, 1))

    def test_missing_linking_map_file_raises(self):
        m = load(LINKING_MAP=str(Path(self.tmp.name) / "absent.md"))
        with self.assertRaises(FileNotFoundError):
            m.is_internal_url("https://sibling.example/x")

    def test_no_local_penalty_when_locale_unconfigured(self):
        bare = load().score_specificity(ARTICLE)
        self.assertEqual(load().local_patterns(), [])
        self.assertFalse(any("local" in i["issue"].lower() for i in bare["issues"]))
        # ARTICLE has no euro amounts, so configuring a currency costs it the local penalty.
        self.assertEqual(load(LOCAL_CURRENCY="€").score_specificity(ARTICLE)["score"], bare["score"] - 10)

    def test_currency_matches_on_either_side(self):
        m = load(LOCAL_CURRENCY="€")
        self.assertEqual(m.score_specificity("Rent is €100 here.")["details"]["local_references"], 1)
        self.assertEqual(m.score_specificity("Rent is 100 € here.")["details"]["local_references"], 1)


if __name__ == "__main__":
    unittest.main()
