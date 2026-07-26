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


def documento_scaduto_privacy_message(cliente):
    """Avviso non bloccante in stampa Privacy: chiedere documento in corso di validità."""
    scadenza = getattr(cliente, "documento_data_scadenza", None) if cliente else None
    scadenza_label = scadenza.strftime("%d/%m/%Y") if scadenza else ""
    nome = ""
    if cliente:
        nome = (
            getattr(cliente, "display_name", None)
            or (cliente.ragione_sociale or f"{cliente.cognome} {cliente.nome}").strip()
        )
    soggetto = f" di {nome}" if nome else ""
    if scadenza_label:
        return (
            f"Attenzione: il documento di identità{soggetto} è scaduto il {scadenza_label}. "
            "Richiedi un documento corretto in corso di validità prima di procedere con la stampa."
        )
    return (
        f"Attenzione: il documento di identità{soggetto} risulta scaduto. "
        "Richiedi un documento corretto in corso di validità prima di procedere con la stampa."
    )
