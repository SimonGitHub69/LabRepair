from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from apps.core.version import get_version


class VersioneProgrammaTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="tester", password="pass")
        perm = Permission.objects.get(codename="access_sistema")
        self.user.user_permissions.add(perm)

    def _login(self):
        self.client.force_login(self.user)
        session = self.client.session
        session["negozio"] = "PT"
        session.save()

    def test_login_mostra_versione(self):
        response = self.client.get("/login/")
        self.assertContains(response, get_version())

    def test_login_mostra_occhiolino_password(self):
        response = self.client.get("/login/")
        self.assertContains(response, 'data-password-toggle')
        self.assertContains(response, "Mostra password")
        self.assertContains(response, "ti-eye")

    def test_sistema_mostra_versione(self):
        self._login()
        response = self.client.get(reverse("dashboard:sistema"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, get_version())
        self.assertContains(response, "Novità")

    def test_novita_mostra_changelog(self):
        self._login()
        response = self.client.get(reverse("dashboard:novita"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, get_version())
        self.assertContains(response, "cronologia delle modifiche")


class ReportMenuTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="report_user", password="pass")
        perm = Permission.objects.get(codename="access_report")
        self.user.user_permissions.add(perm)

    def _login(self):
        self.client.force_login(self.user)
        session = self.client.session
        session["negozio"] = "PT"
        session.save()

    def test_report_mostra_operazione_non_disponibile(self):
        self._login()
        response = self.client.get(reverse("dashboard:report"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Operazione non disponibile")
