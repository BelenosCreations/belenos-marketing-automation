"""Standard-library branding validation; runs in the normal offline test workflow."""
from pathlib import Path
import json
import hashlib
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

    def test_android_packages_exact_approved_artwork_and_not_legacy_logo(self):
        packaged = ROOT / "android" / "app" / "src" / "main" / "res"
        expected = {
            "bam_approved_metallic_primary.webp":
                "ef3e65e4a643a7062badd3885575068dea3055a750ef43447477afbe429ca393",
            "bam_approved_launcher_foreground.webp":
                "005c6de6b6db298aae39710a78a950a556d6072868f7a55e641b560e6a8e39df",
            "bam_approved_flat_lockup.webp":
                "2211406155d32c56a3ccecda6e6a25ad4378c21eb7de4e465feec8ccb09441ba",
        }
        for filename, wanted_sha in expected.items():
            with self.subTest(filename=filename):
                asset = packaged / "drawable-nodpi" / filename
                self.assertTrue(asset.exists(), filename)
                blob = asset.read_bytes()
                self.assertEqual(b"RIFF", blob[:4])
                self.assertEqual(b"WEBP", blob[8:12])
                self.assertEqual(wanted_sha, hashlib.sha256(blob).hexdigest())
        for legacy in ("bam_wordmark_dark.png", "bam_launcher_foreground.png",
                       "bam_launcher_monochrome.png"):
            self.assertFalse((packaged / "drawable-nodpi" / legacy).exists())

        app_header = (ROOT / "android" / "app" / "src" / "main" / "java" /
                      "com" / "belenos" / "bam" / "MainActivity.kt").read_text()
        self.assertIn("setImageResource(R.drawable.bam_approved_metallic_primary)",
                      app_header)
        self.assertNotIn("R.drawable.bam_wordmark_dark", app_header)
        android = "{http://schemas.android.com/apk/res/android}"
        foreground = ET.parse(packaged / "drawable" / "bam_launcher_safe_foreground.xml").getroot()
        self.assertEqual("inset", foreground.tag)
        self.assertEqual("@drawable/bam_approved_launcher_foreground",
                         foreground.attrib[android + "drawable"])
        self.assertEqual("14%", foreground.attrib[android + "inset"])
        for icon in ("ic_launcher.xml", "ic_launcher_round.xml"):
            root = ET.parse(packaged / "mipmap-anydpi-v26" / icon).getroot()
            names = [element.tag for element in root]
            self.assertEqual(["background", "foreground"], names)
            self.assertEqual("@drawable/bam_launcher_safe_foreground",
                             root.find("foreground").attrib[android + "drawable"])
            self.assertIsNone(root.find("monochrome"))

    def test_adaptive_icons_reference_bundled_resources(self):
        for name in ("ic_launcher.xml", "ic_launcher_round.xml"):
            root = ET.parse(TEMPLATES / "mipmap-anydpi-v26" / name).getroot()
            self.assertEqual(root.tag, "adaptive-icon")
            self.assertEqual(len(root), 3)
            self.assertEqual({x.tag for x in root}, {"background", "foreground", "monochrome"})
        self.assertIn('name="bam_icon_background"', (TEMPLATES / "values" / "colors.xml").read_text())


if __name__ == "__main__":
    unittest.main()
