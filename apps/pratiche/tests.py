from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.anagrafiche.models import Anagrafica
from apps.pratiche.models import Pratica


class ClienteContattiUpdateTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="op", password="op")
        self.client.force_login(self.user)
        session = self.client.session
        session["negozio"] = "PT"
        session.save()
        self.cliente = Anagrafica.objects.create(
            tipo=Anagrafica.Tipo.CLIENTE,
            cognome="ROSSI",
            nome="Mario",
            telefono="0573000000",
            cellulare="3330000000",
            email="old@example.com",
        )
        self.pratica = Pratica.objects.create(
            codice="T-CONTATTI-1",
            negozio="PT",
            cliente=self.cliente,
            referente_cognome="ROSSI",
            referente_nome="Mario",
            referente_telefono="0573000000",
            referente_cellulare="3330000000",
            referente_email="old@example.com",
            busta_stampata_il=timezone.now(),
        )

    def test_aggiorna_solo_recapiti_anche_con_testata_bloccata(self):
        url = reverse("pratiche:cliente_contatti_update", kwargs={"pk": self.cliente.pk})
        response = self.client.post(
            url,
            {
                "telefono": "0573111111",
                "cellulare": "3331111111",
                "email": "nuovo@example.com",
                "pratica": self.pratica.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.cliente.refresh_from_db()
        self.pratica.refresh_from_db()
        self.assertEqual(self.cliente.telefono, "0573111111")
        self.assertEqual(self.cliente.cellulare, "3331111111")
        self.assertEqual(self.cliente.email, "nuovo@example.com")
        self.assertEqual(self.cliente.cognome, "ROSSI")
        self.assertEqual(self.cliente.nome, "Mario")
        self.assertEqual(self.pratica.referente_telefono, "0573111111")
        self.assertEqual(self.pratica.referente_cellulare, "3331111111")
        self.assertEqual(self.pratica.referente_email, "nuovo@example.com")
        self.assertEqual(self.pratica.referente_cognome, "ROSSI")
        self.assertEqual(self.pratica.referente_nome, "Mario")

    def test_email_non_valida_non_salva(self):
        url = reverse("pratiche:cliente_contatti_update", kwargs={"pk": self.cliente.pk})
        response = self.client.post(
            url,
            {
                "telefono": "0573111111",
                "cellulare": "",
                "email": "non-valida",
                "pratica": self.pratica.pk,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.email, "old@example.com")
        self.assertEqual(self.cliente.telefono, "0573000000")

    def test_scheda_mostra_modifica_cliente(self):
        url = reverse("pratiche:pratica_update", kwargs={"pk": self.pratica.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Modifica Cliente")
        self.assertContains(response, "clienteContattiTelefono")
        self.assertContains(response, "clienteContattiCellulare")
        self.assertContains(response, "clienteContattiEmail")
