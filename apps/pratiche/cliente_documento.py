from django.utils import timezone


def is_documento_identita_scaduto(cliente):
    """True se la data di scadenza documento è anteriore a oggi."""
    if not cliente:
        return False

    scadenza = getattr(cliente, "documento_data_scadenza", None)
    if scadenza is None:
        return False

    return scadenza < timezone.localdate()


def documento_scaduto_message(cliente, *, bloccante=False):
    scadenza = cliente.documento_data_scadenza
    scadenza_label = scadenza.strftime("%d/%m/%y") if scadenza else ""
    nome = (cliente.ragione_sociale or f"{cliente.cognome} {cliente.nome}").strip()
    if bloccante:
        if scadenza_label:
            return (
                f"Il documento di identità di {nome} è scaduto il {scadenza_label}. "
                "Aggiornalo e premi «Salva documento», oppure usa «Forza registrazione» "
                "per creare comunque la riparazione preziosa."
            )
        return (
            f"Il documento di identità di {nome} risulta scaduto. "
            "Aggiornalo e premi «Salva documento», oppure usa «Forza registrazione» "
            "per creare comunque la riparazione preziosa."
        )
    if scadenza_label:
        return (
            f"Il documento di identità di {nome} è scaduto il {scadenza_label}. "
            "Puoi aggiornarlo nella sezione «Documento di identità» "
            "(non blocca il salvataggio della riparazione)."
        )
    return (
        f"Il documento di identità di {nome} risulta scaduto. "
        "Puoi aggiornarlo nella sezione «Documento di identità» "
        "(non blocca il salvataggio della riparazione)."
    )


def documento_scaduto_privacy_message(cliente):
    """Avviso non bloccante in stampa Privacy: chiedere documento in corso di validità."""
    scadenza = getattr(cliente, "documento_data_scadenza", None) if cliente else None
    scadenza_label = scadenza.strftime("%d/%m/%y") if scadenza else ""
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
