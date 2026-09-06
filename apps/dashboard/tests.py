from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse


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
