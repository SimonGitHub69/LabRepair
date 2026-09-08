from django.test import SimpleTestCase

from apps.core.version import get_changelog_entries, get_version


class VersionTests(SimpleTestCase):
    def test_version_is_semver(self):
        self.assertRegex(get_version(), r"^\d+\.\d+\.\d+")

    def test_changelog_starts_with_current_version(self):
        entries = get_changelog_entries()
        self.assertTrue(entries)
        self.assertEqual(entries[0]["version"], get_version())
        self.assertTrue(entries[0]["sections"])
