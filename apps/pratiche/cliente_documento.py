from django.utils import timezone


def is_documento_identita_scaduto(cliente):
    """True se la data di scadenza documento è anterioriore a oggi."""
    if not cliente:
        return False

    scadenza = getattr(cliente, "documento_data_scadenza", None)
    if scadenza is None:
        return False

    return scadenza < timezone.localdate()


def documento_scaduto_message(cliente):
    scadenza = cliente.documento_data_scadenza
    scadenza_label = scadenza.strftime("%d/%m/%Y") if scadenza else ""
    nome = (cliente.ragione_sociale or f"{cliente.cognome} {cliente.nome}").strip()
    if scadenza_label:
        return (
            f"Il documento di identità di {nome} è scaduto il {scadenza_label}. "
            "Aggiorna la scheda anagrafica con un documento in corso di validità "
            "prima di proseguire con la riparazione preziosa."
        )
    return (
        f"Il documento di identità di {nome} risulta scaduto. "
        "Aggiorna la scheda anagrafica prima di proseguire con la riparazione preziosa."
    )
