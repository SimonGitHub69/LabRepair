from datetime import timedelta
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.anagrafiche.models import Anagrafica
from apps.pratiche.forms import PraticaForm
from apps.pratiche.gs_articoli import format_gs_descrizione
from apps.pratiche.models import Operatore, Pratica, TipoOggetto


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


class OperatoreMancanteSuTestataBloccataTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="op2", password="op")
        self.client.force_login(self.user)
        session = self.client.session
        session["negozio"] = "PT"
        session.save()
        self.tipo = TipoOggetto.objects.create(denominazione="Anello test op", um="gr")
        self.operatore = Operatore.objects.create(nominativo="Mario Test")
        self.altro = Operatore.objects.create(nominativo="Luigi Test")
        self.cliente = Anagrafica.objects.create(
            tipo=Anagrafica.Tipo.CLIENTE,
            cognome="ROSSI",
            nome="Mario",
            cellulare="3330000000",
        )
        today = timezone.localdate()
        self.pratica = Pratica.objects.create(
            codice="T-NO-OP",
            negozio="PT",
            cliente=self.cliente,
            referente_cognome="ROSSI",
            referente_nome="Mario",
            referente_cellulare="3330000000",
            tipo_oggetto=self.tipo,
            descrizione="Anello di prova",
            data_apertura=today,
            data_scadenza=today + timedelta(days=7),
            busta_stampata_il=timezone.now(),
        )

    def _data(self, operatore_id):
        pratica = self.pratica
        return {
            "operatore": str(operatore_id),
            "cliente": str(self.cliente.pk),
            "referente_cognome": pratica.referente_cognome,
            "referente_nome": pratica.referente_nome,
            "referente_telefono": "",
            "referente_cellulare": pratica.referente_cellulare,
            "referente_email": "",
            "riparatore": "",
            "centro_assistenza": "",
            "data_apertura": pratica.data_apertura.isoformat(),
            "tipologia": pratica.tipologia,
            "tipo_oggetto": str(self.tipo.pk),
            "descrizione": pratica.descrizione,
            "data_scadenza": pratica.data_scadenza.isoformat(),
            "peso_grammi": "0",
            "tipo_metallo": "",
            "stato": pratica.stato,
            "priorita": pratica.priorita,
            "data_riparatore": "",
            "data_rientro": "",
            "costo_lavorazione": "0",
            "costo_materiale": "0",
            "oro_aggiunto": "0",
            "prezzo_unita": "0",
            "prezzo_al": "0",
            "prezzo_pagato": "0",
            "numero_scontrino": "",
            "data_vendita": "",
        }

    def test_apertura_operatore_editabile_solo_se_manca(self):
        url = reverse("pratiche:pratica_update", kwargs={"pk": self.pratica.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertFalse(form.fields["operatore"].disabled)
        self.assertTrue(form.fields["referente_cognome"].disabled)
        self.assertContains(response, "puoi inserirlo anche con la busta già stampata")

    def test_salva_operatore_mancante_con_busta_stampata(self):
        form = PraticaForm(self._data(self.operatore.pk), instance=self.pratica)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.pratica.refresh_from_db()
        self.assertEqual(self.pratica.operatore_id, self.operatore.pk)
        self.assertEqual(self.pratica.referente_cognome, "ROSSI")

    def test_operatore_gia_presente_non_si_cambia(self):
        self.pratica.operatore = self.operatore
        self.pratica.save(update_fields=["operatore"])
        form = PraticaForm(self._data(self.altro.pk), instance=self.pratica)
        self.assertTrue(form.fields["operatore"].disabled)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.pratica.refresh_from_db()
        self.assertEqual(self.pratica.operatore_id, self.operatore.pk)


class ComunicazioneSalvataggioJsonTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="op3", password="op")
        self.client.force_login(self.user)
        session = self.client.session
        session["negozio"] = "PT"
        session.save()
        self.pratica = Pratica.objects.create(
            codice="T-COM-1",
            negozio="PT",
            referente_cognome="ROSSI",
            referente_nome="Mario",
            referente_cellulare="3330000000",
            descrizione="Anello",
        )

    def test_salva_comunicazione_json_per_scorciatoia(self):
        url = reverse("pratiche:comunicazione_create", kwargs={"pratica_pk": self.pratica.pk})
        quando = timezone.localtime().replace(second=0, microsecond=0)
        response = self.client.post(
            url,
            {
                "descrizione": "Nota scritta insieme alla scheda",
                "data_ora": quando.strftime("%Y-%m-%dT%H:%M"),
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(
            self.pratica.comunicazioni.filter(is_active=True).count(),
            1,
        )
        self.assertEqual(
            self.pratica.comunicazioni.get().descrizione,
            "Nota scritta insieme alla scheda",
        )

    def test_comunicazione_vuota_non_salva(self):
        url = reverse("pratiche:comunicazione_create", kwargs={"pratica_pk": self.pratica.pk})
        response = self.client.post(
            url,
            {"descrizione": "", "data_ora": ""},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_ACCEPT="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])
        self.assertEqual(self.pratica.comunicazioni.count(), 0)


class GsDescrizioneTests(SimpleTestCase):
    def test_prz_descr_senza_caratteri_di_controllo(self):
        pratica = SimpleNamespace(
            tipo_oggetto_id=1,
            tipo_oggetto=SimpleNamespace(denominazione="Anello"),
            descrizione="oro\r\n18kt\tcon\x00pietra\u2028e accento è",
            titolo="",
        )
        text = format_gs_descrizione(pratica)
        self.assertNotIn("\r", text)
        self.assertNotIn("\n", text)
        self.assertNotIn("\t", text)
        self.assertNotIn("\x00", text)
        self.assertNotIn("\u2028", text)
        self.assertEqual(text, "Anello - oro 18kt con pietra e accento è")
        self.assertLessEqual(len(text), 50)
