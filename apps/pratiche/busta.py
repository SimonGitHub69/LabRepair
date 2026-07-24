def format_busta_date(value):
    if not value:
        return "00/00/00"
    return value.strftime("%d/%m/%y")


def _format_peso(value):
    if value in (None, 0):
        return ""
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return text


def _format_cliente_busta(pratica):
    if pratica.cliente_id:
        cognome = (pratica.cliente.cognome or "").strip()
        nome = (pratica.cliente.nome or "").strip()
        if cognome or nome:
            return " ".join(p for p in (cognome, nome) if p).upper()
        return pratica.cliente.display_name.upper()

    cognome = (pratica.referente_cognome or "").strip()
    nome = (pratica.referente_nome or "").strip()
    if cognome or nome:
        return " ".join(p for p in (cognome, nome) if p).upper()
    return ""


def build_busta_context(pratica):
    from apps.pratiche.riparatori import is_assistenza_riparatore

    oggetto = ""
    if pratica.tipo_oggetto_id:
        oggetto = pratica.tipo_oggetto.denominazione
    elif pratica.titolo:
        oggetto = pratica.titolo

    is_assistenza = is_assistenza_riparatore(pratica.riparatore)
    if pratica.riparatore_id:
        if is_assistenza:
            riparatore = "ASSISTENZA"
            centro_assistenza = (
                (pratica.centro_assistenza.ragione_sociale or "").strip().upper()
                if pratica.centro_assistenza_id
                else ""
            )
        else:
            riparatore = str(pratica.riparatore).upper()
            centro_assistenza = ""
    else:
        riparatore = ""
        centro_assistenza = ""

    return {
        "compilatore": pratica.operatore.nominativo if pratica.operatore_id else "",
        "arrivato_il": format_busta_date(pratica.data_apertura),
        "consegna_prevista": format_busta_date(pratica.data_scadenza),
        "codice": pratica.codice,
        "barcode_value": f"*{pratica.codice}*",
        "cliente": _format_cliente_busta(pratica),
        "descrizione": pratica.descrizione or "",
        "peso": _format_peso(pratica.peso_grammi),
        "oggetto": oggetto.upper(),
        "riparatore": riparatore,
        "centro_assistenza": centro_assistenza,
        "is_assistenza": is_assistenza,
    }
