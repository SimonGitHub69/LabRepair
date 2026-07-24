ASSISTENZA_RIPARATORE_DENOMINAZIONE = "ASSISTENZA"


def is_assistenza_riparatore(riparatore):
    if not riparatore:
        return False
    return (
        riparatore.denominazione.strip().upper()
        == ASSISTENZA_RIPARATORE_DENOMINAZIONE
    )


def get_assistenza_riparatore_id():
    from apps.pratiche.models import StudioTecnico

    return (
        StudioTecnico.objects.filter(
            is_active=True,
            denominazione__iexact=ASSISTENZA_RIPARATORE_DENOMINAZIONE,
        )
        .values_list("pk", flat=True)
        .first()
    )
