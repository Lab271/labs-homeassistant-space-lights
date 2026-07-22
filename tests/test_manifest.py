"""Validate the integration manifest(s) — catches the breakage that hassfest
and HACS validation would reject. Pure JSON checks, no Home Assistant import.
"""
import json
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_MANIFESTS = sorted((_ROOT / "custom_components").glob("*/manifest.json"))

_VALID_IOT_CLASSES = {
    "assumed_state", "cloud_polling", "cloud_push",
    "local_polling", "local_push", "calculated",
}


class ManifestTest(unittest.TestCase):
    def test_manifest_present(self):
        self.assertTrue(_MANIFESTS, "no custom_components/*/manifest.json found")

    def test_manifests_are_valid(self):
        for mf in _MANIFESTS:
            with self.subTest(manifest=str(mf.relative_to(_ROOT))):
                data = json.loads(mf.read_text())
                # domain must match the folder name
                self.assertEqual(data.get("domain"), mf.parent.name)
                # keys hassfest / HACS expect
                for key in ("domain", "name", "documentation",
                            "codeowners", "version", "iot_class"):
                    self.assertIn(key, data, f"missing '{key}'")
                self.assertRegex(data["version"], r"^\d+\.\d+\.\d+")
                self.assertIsInstance(data["codeowners"], list)
                self.assertTrue(data["codeowners"], "codeowners must not be empty")
                self.assertIsInstance(data.get("dependencies", []), list)
                self.assertIsInstance(data.get("requirements", []), list)
                self.assertIn(data["iot_class"], _VALID_IOT_CLASSES)


if __name__ == "__main__":
    unittest.main()
