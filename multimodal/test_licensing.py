from __future__ import annotations

import unittest

from collect import ALLOWED, extension_from_url, safe_name, valid_url
from export_objaverse_xl import canonical_license
from export_wikimedia import license_name


class LicensePolicyTests(unittest.TestCase):
    def test_default_allowlist_is_narrow(self) -> None:
        self.assertEqual(ALLOWED, {"CC0-1.0", "CC-BY-4.0"})

    def test_wikimedia_cc0_and_by4_are_normalized(self) -> None:
        self.assertEqual(license_name("CC0 1.0 Universal"), "CC0-1.0")
        self.assertEqual(license_name("CC BY 4.0"), "CC-BY-4.0")

    def test_wikimedia_restricted_licenses_are_not_allowlisted(self) -> None:
        self.assertEqual(license_name("CC BY-SA 4.0"), "CC-BY-SA-4.0")
        self.assertNotIn(license_name("CC BY-NC 4.0"), ALLOWED)
        self.assertNotIn(license_name("CC BY-SA 4.0"), ALLOWED)

    def test_objaverse_license_aliases_are_normalized(self) -> None:
        self.assertEqual(canonical_license("by"), "CC-BY-4.0")
        self.assertEqual(canonical_license("by 4.0"), "CC-BY-4.0")
        self.assertEqual(canonical_license("CC BY 4.0"), "CC-BY-4.0")
        self.assertEqual(canonical_license("CC0 1.0"), "CC0-1.0")

    def test_objaverse_nc_sa_and_nd_are_rejected(self) -> None:
        self.assertNotIn(canonical_license("CC BY-NC 4.0"), ALLOWED)
        self.assertNotIn(canonical_license("CC BY-SA 4.0"), ALLOWED)
        self.assertNotIn(canonical_license("CC BY-ND 4.0"), ALLOWED)
        self.assertNotIn(canonical_license("unknown"), ALLOWED)

    def test_download_urls_must_be_https_and_nonlocal(self) -> None:
        self.assertTrue(valid_url("https://upload.wikimedia.org/example.jpg"))
        self.assertFalse(valid_url("http://upload.wikimedia.org/example.jpg"))
        self.assertFalse(valid_url("https://localhost/example.jpg"))
        self.assertFalse(valid_url("https://127.0.0.1/example.jpg"))

    def test_extension_can_be_read_from_smithsonian_query(self) -> None:
        self.assertEqual(
            extension_from_url("https://ids.si.edu/ids/download?id=MODEL_IMAGE_001.jpg"),
            ".jpg",
        )

    def test_asset_names_are_path_safe(self) -> None:
        self.assertNotIn("/", safe_name("../../unsafe/path"))
        self.assertNotIn("\\", safe_name("..\\unsafe\\path"))


if __name__ == "__main__":
    unittest.main()
