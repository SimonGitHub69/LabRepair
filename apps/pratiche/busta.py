import base64
import io


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


def _build_barcode_data_uri(codice):
    """PNG Code39 inline: affidabile in anteprima e stampa agent (senza font)."""
    from barcode import Code39
    from barcode.writer import ImageWriter

    # Sul barcode niente trattino (P26-0039 → P260039); il testo sopra resta invariato.
    text = "".join(ch for ch in (codice or "").strip() if ch != "-")
    if not text:
        return ""

    buffer = io.BytesIO()
    Code39(text, writer=ImageWriter(), add_checksum=False).write(
        buffer,
        options={
            # Barre più strette (prima 0.28): densità più alta, barcode più corto
            "module_width": 0.16,
            "module_height": 10,
            "quiet_zone": 0.3,
            "write_text": False,
            "dpi": 300,
        },
    )
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


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

    codice = pratica.codice or ""
    barcode_text = "".join(ch for ch in codice if ch != "-")
    return {
        "compilatore": pratica.operatore.nominativo if pratica.operatore_id else "",
        "arrivato_il": format_busta_date(pratica.data_apertura),
        "consegna_prevista": format_busta_date(pratica.data_scadenza),
        "codice": codice,
        "barcode_value": f"*{barcode_text}*" if barcode_text else "",
        "barcode_data_uri": _build_barcode_data_uri(codice),
        "cliente": _format_cliente_busta(pratica),
        "descrizione": pratica.descrizione or "",
        "peso": _format_peso(pratica.peso_grammi),
        "oggetto": oggetto.upper(),
        "riparatore": riparatore,
        "centro_assistenza": centro_assistenza,
        "is_assistenza": is_assistenza,
        "ddt_numero": (pratica.ddt_numero or "").strip(),
        "ddt_data": format_busta_date(pratica.ddt_data) if pratica.ddt_data else "",
        "urgente": pratica.priorita == pratica.Priorita.URGENTE,
    }
