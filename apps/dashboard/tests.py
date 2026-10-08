from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

import csv
import io
import zipfile

from apps.core.negozi import negozio_label
from apps.core.version import get_version
from apps.dashboard.statistica import build_statistica
from apps.dashboard.statistica_export import export_table, render_csv, render_xlsx
from apps.pratiche.models import Pratica


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

    def test_menu_analisi_mostra_statistica(self):
        self._login()
        response = self.client.get(reverse("dashboard:statistica"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Statistica")
        self.assertContains(response, "Numero riparazioni")
        self.assertContains(response, "Prezzo al pubblico")
        self.assertContains(response, "Prezzo pagato")
        self.assertContains(response, "Costo totale")
        self.assertContains(response, "Giorno")
        self.assertContains(response, "Mese")
        self.assertContains(response, "Anno")
        self.assertContains(response, "CSV")
        self.assertContains(response, "Excel")
        self.assertContains(response, reverse("dashboard:statistica_export"))
        self.assertNotContains(response, 'href="/report/"')


class StatisticaRiparazioniTests(TestCase):
    def setUp(self):
        Pratica.objects.create(
            codice="STAT-PT-1",
            negozio="PT",
            data_apertura=date(2026, 10, 1),
            prezzo_al=Decimal("100.00"),
            prezzo_pagato=Decimal("80.00"),
            costo_lavorazione=Decimal("10.00"),
            costo_materiale=Decimal("5.00"),
            oro_aggiunto=Decimal("2.00"),
            prezzo_unita=Decimal("3.00"),
            descrizione="Uno",
        )
        Pratica.objects.create(
            codice="STAT-PT-2",
            negozio="PT",
            data_apertura=date(2026, 10, 1),
            prezzo_al=Decimal("50.50"),
            prezzo_pagato=Decimal("10.00"),
            costo_lavorazione=Decimal("20.00"),
            costo_materiale=Decimal("0.00"),
            descrizione="Due",
        )
        Pratica.objects.create(
            codice="STAT-MO-1",
            negozio="MO",
            data_apertura=date(2026, 10, 2),
            prezzo_al=Decimal("20.00"),
            prezzo_pagato=Decimal("20.00"),
            costo_lavorazione=Decimal("4.00"),
            costo_materiale=Decimal("1.50"),
            descrizione="Tre",
        )
        self.pistoia = negozio_label("PT")
        self.montale = negozio_label("MO")

    def test_raggruppa_per_negozio_e_giorno(self):
        payload = build_statistica("giorno", date(2026, 10, 1), date(2026, 10, 2))
        by_code = {series["codice"]: series for series in payload["series"]}
        self.assertEqual(payload["labels"], ["01/10", "02/10"])
        self.assertEqual(by_code["PT"]["numero"], [2, 0])
        self.assertEqual(by_code["PT"]["prezzo_pubblico"], [150.5, 0.0])
        self.assertEqual(by_code["PT"]["prezzo_pagato"], [90.0, 0.0])
        self.assertEqual(by_code["PT"]["costo_totale"], [41.0, 0.0])
        self.assertEqual(by_code["MO"]["numero"], [0, 1])
        self.assertEqual(by_code["MO"]["prezzo_pubblico"], [0.0, 20.0])
        self.assertEqual(by_code["MO"]["prezzo_pagato"], [0.0, 20.0])
        self.assertEqual(by_code["MO"]["costo_totale"], [0.0, 5.5])

    def _login(self):
        User = get_user_model()
        user = User.objects.create_user(username="stat_export", password="pass")
        perm = Permission.objects.get(codename="access_report")
        user.user_permissions.add(perm)
        self.client.force_login(user)
        session = self.client.session
        session["negozio"] = "PT"
        session.save()

    def _payload(self):
        return build_statistica("giorno", date(2026, 10, 1), date(2026, 10, 2))

    def test_export_tabella_con_totali(self):
        headers, kinds, rows = export_table(self._payload())
        pistoia_numero = headers.index(f"{self.pistoia} - Numero riparazioni")
        pistoia_pubblico = headers.index(f"{self.pistoia} - Prezzo al pubblico")
        pistoia_pagato = headers.index(f"{self.pistoia} - Prezzo pagato")
        montale_numero = headers.index(f"{self.montale} - Numero riparazioni")
        totale_numero = headers.index("Totale - Numero riparazioni")
        totale_pubblico = headers.index("Totale - Prezzo al pubblico")
        self.assertEqual(rows[0][0], "01/10")
        self.assertEqual(rows[0][pistoia_numero], 2)
        self.assertEqual(rows[0][pistoia_pubblico], Decimal("150.50"))
        self.assertEqual(rows[0][pistoia_pagato], Decimal("90.00"))
        self.assertEqual(rows[1][montale_numero], 1)
        self.assertEqual(rows[-1][0], "Totale")
        self.assertEqual(rows[-1][pistoia_numero], 2)
        self.assertEqual(rows[-1][montale_numero], 1)
        self.assertEqual(rows[-1][totale_numero], 3)
        self.assertEqual(rows[-1][totale_pubblico], Decimal("170.50"))
        self.assertEqual(kinds[pistoia_numero], "int")
        self.assertEqual(kinds[pistoia_pubblico], "money")

    def test_export_csv_e_xlsx(self):
        payload = self._payload()
        csv_text = render_csv(payload).decode("utf-8-sig")
        parsed = list(csv.reader(io.StringIO(csv_text), delimiter=";"))
        header = parsed[0]
        first = parsed[1]
        last = parsed[-1]
        self.assertEqual(first[header.index(f"{self.pistoia} - Prezzo al pubblico")], "150,50")
        self.assertEqual(last[header.index("Totale - Prezzo al pubblico")], "170,50")
        self.assertEqual(last[header.index("Totale - Prezzo pagato")], "110,00")
        self.assertEqual(last[header.index("Totale - Costo totale")], "46,50")

        with zipfile.ZipFile(io.BytesIO(render_xlsx(payload))) as archive:
            sheet = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
        self.assertIn(f"{self.pistoia} - Numero riparazioni", sheet)
        self.assertIn(">150.50<", sheet)
        self.assertIn("Totale", sheet)

    def test_download_csv_e_xlsx(self):
        self._login()
        query = "?g=giorno&dal=2026-10-01&al=2026-10-02"
        csv_response = self.client.get(reverse("dashboard:statistica_export") + query + "&formato=csv")
        self.assertEqual(csv_response.status_code, 200)
        self.assertIn("text/csv", csv_response["Content-Type"])
        self.assertIn(
            'filename="statistica_giorno_2026-10-01_2026-10-02.csv"',
            csv_response["Content-Disposition"],
        )
        self.assertIn(f"{self.pistoia} - Numero riparazioni".encode(), csv_response.content)
        self.assertIn("150,50".encode(), csv_response.content)

        xlsx_response = self.client.get(reverse("dashboard:statistica_export") + query + "&formato=xlsx")
        self.assertEqual(xlsx_response.status_code, 200)
        self.assertIn("spreadsheetml.sheet", xlsx_response["Content-Type"])
        self.assertTrue(xlsx_response.content.startswith(b"PK"))

    def test_export_senza_permesso(self):
        User = get_user_model()
        user = User.objects.create_user(username="stat_no_export", password="pass")
        self.client.force_login(user)
        session = self.client.session
        session["negozio"] = "PT"
        session.save()
        response = self.client.get(reverse("dashboard:statistica_export"))
        self.assertEqual(response.status_code, 403)
