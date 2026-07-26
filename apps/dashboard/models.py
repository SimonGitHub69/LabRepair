from django.db import models


class AccessoMenu(models.Model):
    """
    Modello tecnico solo per i permessi di menu LabRepair.
    Non viene usato come tabella operativa.
    """

    class Meta:
        verbose_name = "Accesso menu"
        verbose_name_plural = "Accessi menu"
        default_permissions = ()
        permissions = [
            ("access_documenti", "Può accedere al menu Documenti"),
            ("access_report", "Può accedere al menu Report"),
            ("access_comandi_vocali", "Può accedere al menu Comandi vocali"),
            ("access_parametri_pc", "Può accedere al menu Parametri PC"),
            ("access_sistema", "Può accedere al menu Sistema"),
        ]

    def __str__(self):
        return "Accesso menu"
