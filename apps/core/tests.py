from django import forms
from django.test import SimpleTestCase
from django.utils import timezone

from apps.core.date_fields import (
    NASCITA_ETA_LIMITE,
    NASCITA_ETA_MAX,
    NASCITA_ETA_MIN,
    shift_years,
    validate_data_nascita,
)
from apps.core.version import get_changelog_entries, get_version


class VersionTests(SimpleTestCase):
    def test_version_is_semver(self):
        self.assertRegex(get_version(), r"^\d+\.\d+\.\d+")

    def test_changelog_starts_with_current_version(self):
        entries = get_changelog_entries()
        self.assertTrue(entries)
        self.assertEqual(entries[0]["version"], get_version())
        self.assertTrue(entries[0]["sections"])


class DataNascitaTests(SimpleTestCase):
    def test_eta_compresa_tra_6_e_100_ok(self):
        today = timezone.localdate()
        validate_data_nascita(shift_years(today, -40))
        validate_data_nascita(shift_years(today, -NASCITA_ETA_MIN))
        validate_data_nascita(shift_years(today, -NASCITA_ETA_MAX))

    def test_rifiuta_eta_inferiore_a_6(self):
        today = timezone.localdate()
        with self.assertRaises(forms.ValidationError) as ctx:
            validate_data_nascita(shift_years(today, -(NASCITA_ETA_MIN - 1)))
        self.assertIn("inferiore a 6", str(ctx.exception))

    def test_rifiuta_eta_oltre_100(self):
        today = timezone.localdate()
        with self.assertRaises(forms.ValidationError) as ctx:
            validate_data_nascita(shift_years(today, -(NASCITA_ETA_MAX + 1)))
        self.assertIn("oltre 100", str(ctx.exception))

    def test_rifiuta_futura_e_oltre_limite(self):
        today = timezone.localdate()
        with self.assertRaises(forms.ValidationError) as ctx:
            validate_data_nascita(shift_years(today, 1))
        self.assertIn("successiva a oggi", str(ctx.exception))
        with self.assertRaises(forms.ValidationError) as ctx:
            validate_data_nascita(shift_years(today, -(NASCITA_ETA_LIMITE + 1)))
        self.assertIn("120", str(ctx.exception))
