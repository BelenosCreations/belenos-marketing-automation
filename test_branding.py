"""Standard-library branding validation; runs in the normal offline test workflow."""
from pathlib import Path
import json
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "branding" / "source"
TEMPLATES = ROOT / "android" / "branding" / "res"


class BrandTests(unittest.TestCase):
    def test_brand_name_and_multi_business_scope(self):
        meta = json.loads((ROOT / "branding" / "palette.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["official_name"], "Belenos Automatic Marketing")
        self.assertEqual(meta["brand"], "BAM")
        self.assertIn("Multi-business", meta["product_scope"])
        self.assertFalse(meta["publishing_enabled"])

    def test_logos_have_correct_full_name(self):
        for name in ("logo_light.svg", "logo_dark.svg"):
            with self.subTest(name=name):
                svg = (SRC / name).read_text(encoding="utf-8")
                self.assertEqual(ET.fromstring(svg).tag, "{http://www.w3.org/2000/svg}svg")
                self.assertIn("Belenos Automatic Marketing", svg)
                self.assertNotIn("Automatic Marketing Automatic Marketing", svg)

    def test_launcher_source_and_safe_foreground_are_valid(self):
        for name in ("app_icon.svg", "adaptive_foreground.svg", "adaptive_monochrome.svg"):
            with self.subTest(name=name):
                root = ET.parse(SRC / name).getroot()
                self.assertTrue(root.attrib["viewBox"])

    def test_adaptive_icons_reference_bundled_resources(self):
        for name in ("ic_launcher.xml", "ic_launcher_round.xml"):
            root = ET.parse(TEMPLATES / "mipmap-anydpi-v26" / name).getroot()
            self.assertEqual(root.tag, "adaptive-icon")
            self.assertEqual(len(root), 3)
            self.assertEqual({x.tag for x in root}, {"background", "foreground", "monochrome"})
        self.assertIn('name="bam_icon_background"', (TEMPLATES / "values" / "colors.xml").read_text())


if __name__ == "__main__":
    unittest.main()
