import io
from pathlib import Path

import fitz
from barcode import Code39
from barcode.writer import ImageWriter
from django.conf import settings
from django.contrib.staticfiles import finders
from django.utils import timezone
from PIL import Image

PRIVACY_PDF_STATIC = "securtek/pdf/scheda_privacy.pdf"
PRIVACY_PDF_FILENAME = "Scheda_Privacy.pdf"

A4_RECT = fitz.paper_rect("a4")
CM = 72 / 2.54
LEFT_MARGIN_CM = 1
LEFT_MARGIN = LEFT_MARGIN_CM * CM
HEADER_TOP_OFFSET_CM = 0.5
HEADER_TOP_OFFSET = HEADER_TOP_OFFSET_CM * CM

PRIVACY_TITLE_TEXT = "SCHEDA RIPARAZIONE"
PRIVACY_TITLE_TEMPLATE_OVERLAY = fitz.Rect(205, 2, 370, 22)
PRIVACY_TITLE_CENTER_X = 286.5
PRIVACY_TITLE_BASELINE_Y = 17 + HEADER_TOP_OFFSET
PRIVACY_TITLE_FONT_SIZE = 14
PRIVACY_CODE_OVERLAY = fitz.Rect(390, 16, 558, 82)
LOGO_OFFSET_UP_MM = 4
LOGO_OFFSET_UP = (LOGO_OFFSET_UP_MM / 10) * CM
PRIVACY_LOGO_LEFT = LEFT_MARGIN
PRIVACY_LOGO_TOP = 10 + HEADER_TOP_OFFSET - LOGO_OFFSET_UP
PRIVACY_LOGO_MAX_WIDTH = 145
PRIVACY_LOGO_MAX_HEIGHT = 32
PRIVACY_LOGO_TEMPLATE_OVERLAY = fitz.Rect(10, 8, 170, 36)
AZIENDA_CLEAR_GAP_MM = 2
HEADER_SEPARATOR_TEMPLATE_OVERLAY = fitz.Rect(8, 90, 562, 94)
HEADER_SEPARATOR_TEMPLATE_Y = 92
HEADER_SEPARATOR_OFFSET_DOWN_MM = 3
HEADER_SEPARATOR_Y = HEADER_SEPARATOR_TEMPLATE_Y + (HEADER_SEPARATOR_OFFSET_DOWN_MM / 10) * CM
HEADER_SEPARATOR_RIGHT = 385
PRIVACY_AZIENDA_OVERLAY = fitz.Rect(10, 34, 200, 34 + 3.2 * CM)
PRIVACY_PREZZO_PAGAMENTO_OVERLAY = fitz.Rect(8, 600, 220, 648)
PRIVACY_TEMPLATE_MID_SEPARATOR_OVERLAY = fitz.Rect(8, 594, 565, 605)
PRIVACY_TEMPLATE_FIRMA_LABEL_OVERLAY = fitz.Rect(450, 605, 520, 622)
OGGETTO_AFTER_PHOTOS_SEPARATOR_GAP_MM = 3
OGGETTO_AFTER_PHOTOS_SEPARATOR_WIDTH = 0.4
OGGETTO_AFTER_PHOTOS_SEPARATOR_RIGHT = 555
FIRMA_LABEL_FONT_SIZE = 9
FIRMA_SIGNATURE_LINE_GAP_MM = 18
FIRMA_SIGNATURE_LINE_LEFT = 410
FIRMA_SIGNATURE_LINE_RIGHT = 555
FIRMA_SIGNATURE_LINE_WIDTH = 0.4
ACCETTAZIONE_LABEL = "Per accettazione"
ACCETTAZIONE_LABEL_FONT_SIZE = 9
ACCETTAZIONE_OFFSET_UP_CM = 2
ACCETTAZIONE_LABEL_BASELINE_Y = 655 - ACCETTAZIONE_OFFSET_UP_CM * CM
ACCETTAZIONE_LINE_GAP_MM = FIRMA_SIGNATURE_LINE_GAP_MM
ACCETTAZIONE_LINE_LEFT = FIRMA_SIGNATURE_LINE_LEFT
ACCETTAZIONE_LINE_RIGHT = FIRMA_SIGNATURE_LINE_RIGHT
ACCETTAZIONE_LINE_WIDTH = FIRMA_SIGNATURE_LINE_WIDTH
PRIVACY_TEMPLATE_ACCETTAZIONE_OVERLAY = fitz.Rect(400, 590, 565, 750)
PRIVACY_TEMPLATE_LEFTOVER_DICHIARAZIONE_OVERLAY = fitz.Rect(440, 668, 560, 686)
PRIVACY_DATA_TEMPLATE_OVERLAY = fitz.Rect(8, 720, 220, 742)
PRIVACY_DATA_OFFSET_UP_CM = 2
PRIVACY_DATA_OFFSET_UP = PRIVACY_DATA_OFFSET_UP_CM * CM
PRIVACY_DATA_OVERLAY = fitz.Rect(
    8,
    720 - PRIVACY_DATA_OFFSET_UP,
    280,
    742 - PRIVACY_DATA_OFFSET_UP,
)
PRIVACY_DATA_BASELINE_Y = 736 - PRIVACY_DATA_OFFSET_UP
CODICE_LETTER_LOCALITA = {
    "P": "PISTOIA",
    "Q": "QUARRATA",
    "M": "MONTALE",
}
NEGOZIO_LOCALITA = {
    "PT": "PISTOIA",
    "QU": "QUARRATA",
    "MO": "MONTALE",
}
RITIRO_FIRMA_TITLE = "Riparazione Ritirata"
RITIRO_FIRMA_DATA_LABEL = "in data .........................................."
RITIRO_FIRMA_FONT_SIZE = 9
RITIRO_FIRMA_LINE_HEIGHT = 16
RITIRO_FIRMA_OFFSET_UP_CM = 3
RITIRO_FIRMA_OFFSET_UP = RITIRO_FIRMA_OFFSET_UP_CM * CM
RITIRO_FIRMA_TITLE_EXTRA_UP_MM = 3
RITIRO_FIRMA_TITLE_BASELINE_Y = (
    815
    - RITIRO_FIRMA_OFFSET_UP
    - (RITIRO_FIRMA_TITLE_EXTRA_UP_MM / 10) * CM
)
RITIRO_FIRMA_DATA_BASELINE_Y = (
    RITIRO_FIRMA_TITLE_BASELINE_Y
    + RITIRO_FIRMA_LINE_HEIGHT
    + (RITIRO_FIRMA_TITLE_EXTRA_UP_MM / 10) * CM
)
RITIRO_FIRMA_LINE_Y = (
    RITIRO_FIRMA_DATA_BASELINE_Y
    + (FIRMA_SIGNATURE_LINE_GAP_MM / 10) * CM
)
RITIRO_FIRMA_LINE_LEFT = 410
RITIRO_FIRMA_LINE_RIGHT = 555
RITIRO_FIRMA_LINE_WIDTH = 0.4
PRIVACY_DICHIARAZIONE_OFFSET_UP_CM = 8
PRIVACY_DICHIARAZIONE_OFFSET_UP = PRIVACY_DICHIARAZIONE_OFFSET_UP_CM * CM
PRIVACY_DICHIARAZIONE_TEMPLATE_OVERLAY = fitz.Rect(8, 668, 445, 700)
PRIVACY_DICHIARAZIONE_OVERLAY = fitz.Rect(
    8,
    658 - PRIVACY_DICHIARAZIONE_OFFSET_UP,
    445,
    725 - PRIVACY_DICHIARAZIONE_OFFSET_UP,
)
PRIVACY_DICHIARAZIONE_AREA = fitz.Rect(
    LEFT_MARGIN,
    660 - PRIVACY_DICHIARAZIONE_OFFSET_UP,
    440,
    725 - PRIVACY_DICHIARAZIONE_OFFSET_UP,
)
FIRMA_LABEL_BASELINE_Y = (
    PRIVACY_DICHIARAZIONE_AREA.y0 + FIRMA_LABEL_FONT_SIZE
)
FIRMA_LINE_Y = (
    FIRMA_LABEL_BASELINE_Y
    + (FIRMA_SIGNATURE_LINE_GAP_MM / 10) * CM
)
PRIVACY_DICHIARAZIONE_FONT_SIZE = 10.1
PRIVACY_DICHIARAZIONE_DEFAULT = (
    "Il sottoscritto/a dichiara che gli oggetti sopra indicati NON sono di illecita "
    "provenienza e di essere in possesso di tutti i diritti atti alla riparazione/modifica "
    "degli stessi."
)
PRIVACY_DIRITTI_TITLE = "Trattamento dei dati personali"
PRIVACY_DIRITTI_TITLE_FONT_SIZE = PRIVACY_DICHIARAZIONE_FONT_SIZE
PRIVACY_DIRITTI_FONT_SIZE = PRIVACY_DICHIARAZIONE_FONT_SIZE
PRIVACY_DIRITTI_OFFSET_UP_CM = 8
PRIVACY_DIRITTI_OFFSET_UP = PRIVACY_DIRITTI_OFFSET_UP_CM * CM
PRIVACY_DIRITTI_TEMPLATE_OVERLAY = fitz.Rect(8, 738, 555, 810)
PRIVACY_DIRITTI_OVERLAY = fitz.Rect(
    8,
    738 - PRIVACY_DIRITTI_OFFSET_UP,
    FIRMA_SIGNATURE_LINE_LEFT - 2,
    810 - PRIVACY_DIRITTI_OFFSET_UP,
)
PRIVACY_DIRITTI_TITLE_BASELINE_Y = 752 - PRIVACY_DIRITTI_OFFSET_UP
PRIVACY_DIRITTI_TEXT_AREA = fitz.Rect(
    LEFT_MARGIN,
    758 - PRIVACY_DIRITTI_OFFSET_UP,
    555,
    808 - PRIVACY_DIRITTI_OFFSET_UP,
)
PRIVACY_DIRITTI_LEFT = LEFT_MARGIN
CODE_TEXT_FONT_SIZE = 20
CODE_TEXT_RIGHT = 555
CODE_TEXT_BASELINE_Y = 44 + HEADER_TOP_OFFSET
CODE_BARCODE_AREA = fitz.Rect(395, 48 + HEADER_TOP_OFFSET, 555, 78 + HEADER_TOP_OFFSET)
AZIENDA_LEFT = LEFT_MARGIN
AZIENDA_LINE_HEIGHT = 10
AZIENDA_TEMPLATE_BASELINE_Y = 44
AZIENDA_TOP_OFFSET_CM = 1
AZIENDA_FIRST_BASELINE_Y = (
    AZIENDA_TEMPLATE_BASELINE_Y
    + AZIENDA_TOP_OFFSET_CM * CM
    + HEADER_TOP_OFFSET
    - LOGO_OFFSET_UP
)
AZIENDA_RAGIONE_SOCIALE_FONT_SIZE = 8
AZIENDA_LINE_FONT_SIZE = 7
PRIVACY_CLIENTE_TEMPLATE_OVERLAY = fitz.Rect(8, 94, 562, 220)
CLIENTE_BLOCK_GAP_AFTER_SEPARATOR_MM = 2
CLIENTE_LINE_HEIGHT = 11.5
CLIENTE_FONT_SIZE = 10
CLIENTE_PREFIX = "Il sottoscritto/a "
CLIENTE_TEXT_RIGHT = 555
CLIENTE_AFTER_BLOCK_SEPARATOR_GAP_MM = 2
CLIENTE_AFTER_BLOCK_SEPARATOR_WIDTH = 0.4
OGGETTO_GAP_AFTER_SEPARATOR_MM = 3
OGGETTO_LINE_HEIGHT = 14
OGGETTO_FONT_SIZE = 11.5
OGGETTO_TEXT_RIGHT = 555
OGGETTO_DESCRIZIONE_MAX_HEIGHT = 56
OGGETTO_PHOTO_GAP_AFTER_TEXT_MM = 3
OGGETTO_PHOTO_MAX_WIDTH = 255
OGGETTO_PHOTO_MAX_HEIGHT = 145
OGGETTO_PHOTO_GAP = 14
PRIVACY_OGGETTO_TEMPLATE_OVERLAY = fitz.Rect(8, 155, 585, 595)
PRIVACY_DATA_FONT_SIZE = OGGETTO_FONT_SIZE


def _resolve_static_path(static_path):
    resolved = finders.find(static_path)
    if resolved:
        return Path(resolved)
    return Path(settings.BASE_DIR) / "static" / static_path


def get_privacy_pdf_path():
    return _resolve_static_path(PRIVACY_PDF_STATIC)


def get_default_azienda():
    from apps.core.models import Azienda

    return (
        Azienda.objects.filter(is_active=True)
        .order_by("ragione_sociale")
        .first()
    )


def _get_privacy_cliente(pratica):
    if not pratica.cliente_id:
        return None

    from apps.anagrafiche.models import Anagrafica

    return (
        Anagrafica.objects.filter(
            pk=pratica.cliente_id,
            is_active=True,
            tipo=Anagrafica.Tipo.CLIENTE,
        )
        .prefetch_related("indirizzi")
        .first()
    )


def _get_residenza_indirizzo(cliente):
    if not cliente:
        return None

    from apps.anagrafiche.models import Indirizzo

    indirizzi = cliente.indirizzi.filter(is_active=True)
    residenza = (
        indirizzi.filter(tipo=Indirizzo.TipoIndirizzo.RESIDENZA)
        .order_by("-principale", "id")
        .first()
    )
    if residenza:
        return residenza
    principale = indirizzi.filter(principale=True).order_by("id").first()
    if principale:
        return principale
    return indirizzi.order_by("id").first()


def _format_privacy_date(value):
    if not value:
        return "00/00/00"
    return value.strftime("%d/%m/%Y")


def _format_cliente_nome(pratica, cliente):
    if cliente:
        cognome = (cliente.cognome or "").strip()
        nome = (cliente.nome or "").strip()
        if cognome or nome:
            return " ".join(part.upper() for part in (cognome, nome) if part)

    cognome = (pratica.referente_cognome or "").strip()
    nome = (pratica.referente_nome or "").strip()
    return " ".join(part.upper() for part in (cognome, nome) if part)


def _format_luogo_nascita(cliente):
    if not cliente:
        return ""

    luogo = (cliente.luogo_nascita or "").strip()
    provincia = (cliente.provincia_nascita or "").strip()
    if luogo and provincia:
        return f"{luogo} ({provincia})"
    return luogo or (f"({provincia})" if provincia else "")


def _format_residenza_line(cliente):
    indirizzo = _get_residenza_indirizzo(cliente)
    comune = (indirizzo.comune or "").strip() if indirizzo else ""
    provincia = (indirizzo.provincia or "").strip() if indirizzo else ""
    if comune and provincia:
        city = f"{comune} ({provincia})"
    else:
        city = comune or (f"({provincia})" if provincia else "")

    street_parts = []
    if indirizzo:
        if (indirizzo.indirizzo or "").strip():
            street_parts.append(indirizzo.indirizzo.strip())
        if (indirizzo.civico or "").strip():
            street_parts.append(indirizzo.civico.strip())
    street = " ".join(street_parts)
    return f"Residente a {city} in {street}".strip()


def _format_documento_tipo(cliente):
    if not cliente:
        return ""

    tipo = (cliente.documento_tipo_label or "").strip()
    if not tipo:
        tipo = (cliente.documento_tipo or "").strip()
    return tipo


def _format_documento_rilasciato_da_line(cliente):
    if not cliente:
        return "Rilasciato dal:"

    comune = (cliente.documento_comune_rilascio or "").strip()
    if comune:
        if comune.lower().startswith("comune"):
            return f"Rilasciato dal: {comune}"
        return f"Rilasciato dal: Comune di {comune}"

    rilasciato_da = (cliente.documento_rilasciato_da or "").strip()
    if rilasciato_da:
        if rilasciato_da.lower() in {"comune", "comune di"}:
            return "Rilasciato dal: Comune"
        return f"Rilasciato dal: {rilasciato_da}"
    return "Rilasciato dal:"


def _format_documento_date_line(cliente):
    data_rilascio = _format_privacy_date(
        cliente.documento_data_rilascio if cliente else None
    )
    data_scadenza = _format_privacy_date(
        cliente.documento_data_scadenza if cliente else None
    )
    return f"Data Rilascio: {data_rilascio}  Data Scadenza: {data_scadenza}"


def build_cliente_privacy_lines(pratica, cliente):
    nome = _format_cliente_nome(pratica, cliente)
    luogo_nascita = _format_luogo_nascita(cliente)
    data_nascita = _format_privacy_date(cliente.data_nascita if cliente else None)
    nato_line = f"Nato/a {luogo_nascita} il {data_nascita}".strip()
    residente_line = _format_residenza_line(cliente)

    documento_tipo = _format_documento_tipo(cliente)
    documento_numero = (cliente.documento_numero or "").strip() if cliente else ""
    documento_line = "Documento:"
    if documento_tipo:
        documento_line = f"Documento: {documento_tipo}"
    if documento_numero:
        documento_line = f"{documento_line} n. {documento_numero}"

    rilasciato_da_line = _format_documento_rilasciato_da_line(cliente)
    documento_date_line = _format_documento_date_line(cliente)

    codice_fiscale = (cliente.codice_fiscale or "").strip() if cliente else ""
    codice_fiscale_line = f"Cod. Fiscale {codice_fiscale}" if codice_fiscale else ""

    return {
        "nome": nome,
        "nato_line": nato_line,
        "residente_line": residente_line,
        "documento_line": documento_line,
        "rilasciato_da_line": rilasciato_da_line,
        "documento_date_line": documento_date_line,
        "codice_fiscale_line": codice_fiscale_line,
    }


def _cliente_first_baseline():
    return (
        HEADER_SEPARATOR_Y
        + (CLIENTE_BLOCK_GAP_AFTER_SEPARATOR_MM / 10) * CM
        + CLIENTE_FONT_SIZE
    )


def _insert_cliente_block(page, pratica):
    _redact_area(page, PRIVACY_CLIENTE_TEMPLATE_OVERLAY)

    cliente = _get_privacy_cliente(pratica)
    lines = build_cliente_privacy_lines(pratica, cliente)
    baseline_y = _cliente_first_baseline()

    prefix_font = fitz.Font("helv")
    prefix_width = prefix_font.text_length(CLIENTE_PREFIX, fontsize=CLIENTE_FONT_SIZE)
    page.insert_text(
        (LEFT_MARGIN, baseline_y),
        CLIENTE_PREFIX,
        fontsize=CLIENTE_FONT_SIZE,
        fontname="helv",
    )
    page.insert_text(
        (LEFT_MARGIN + prefix_width, baseline_y),
        lines["nome"],
        fontsize=CLIENTE_FONT_SIZE,
        fontname="hebo",
    )

    detail_lines = [
        lines["nato_line"],
        lines["residente_line"],
        lines["documento_line"],
        lines["rilasciato_da_line"],
        lines["documento_date_line"],
    ]
    if lines["codice_fiscale_line"]:
        detail_lines.append(lines["codice_fiscale_line"])

    last_baseline_y = baseline_y
    for index, text in enumerate(detail_lines, start=1):
        last_baseline_y = baseline_y + index * CLIENTE_LINE_HEIGHT
        page.insert_text(
            (
                LEFT_MARGIN,
                last_baseline_y,
            ),
            text,
            fontsize=CLIENTE_FONT_SIZE,
            fontname="helv",
        )

    separator_y = (
        last_baseline_y
        + (CLIENTE_AFTER_BLOCK_SEPARATOR_GAP_MM / 10) * CM
    )
    page.draw_line(
        fitz.Point(LEFT_MARGIN, separator_y),
        fitz.Point(HEADER_SEPARATOR_RIGHT, separator_y),
        color=(0, 0, 0),
        width=CLIENTE_AFTER_BLOCK_SEPARATOR_WIDTH,
    )
    return separator_y


def _format_peso(pratica):
    peso = pratica.peso_grammi if pratica.peso_grammi is not None else 0
    if not peso:
        return ""

    um = "gr"
    if pratica.tipo_oggetto_id and pratica.tipo_oggetto.um:
        um = pratica.tipo_oggetto.um
    text = f"{peso:.3f}".rstrip("0").rstrip(".")
    if not text:
        return ""
    return f"{text} {um}"


def build_oggetto_privacy_lines(pratica):
    tipo_oggetto = ""
    if pratica.tipo_oggetto_id:
        tipo_oggetto = (pratica.tipo_oggetto.denominazione or "").strip()

    tipo_metallo = ""
    if pratica.tipo_metallo:
        tipo_metallo = pratica.get_tipo_metallo_display()

    peso = _format_peso(pratica)
    descrizione = (pratica.descrizione or "").strip()

    return {
        "tipo_oggetto_line": f"Tipo Oggetto: {tipo_oggetto}".strip(),
        "peso_line": f"Peso: {peso}" if peso else "",
        "tipo_metallo_line": f"Tipo Metallo: {tipo_metallo}".strip(),
        "descrizione": descrizione,
    }


def _get_pratica_foto_paths(pratica, limit=2):
    paths = []
    for foto in pratica.foto.filter(is_active=True).order_by("created_at", "id")[:limit]:
        if not foto.immagine:
            continue
        path = Path(foto.immagine.path)
        if path.is_file():
            paths.append(path)
    return paths


def _fit_image_rect(area, img_width, img_height):
    if img_width <= 0 or img_height <= 0:
        return area
    scale = min(area.width / img_width, area.height / img_height)
    width = img_width * scale
    height = img_height * scale
    x0 = area.x0
    y0 = area.y0
    return fitz.Rect(x0, y0, x0 + width, y0 + height)


def _insert_oggetto_block(page, pratica, separator_y):
    _redact_area(
        page,
        fitz.Rect(
            PRIVACY_OGGETTO_TEMPLATE_OVERLAY.x0,
            max(PRIVACY_OGGETTO_TEMPLATE_OVERLAY.y0, separator_y + 1),
            PRIVACY_OGGETTO_TEMPLATE_OVERLAY.x1,
            PRIVACY_OGGETTO_TEMPLATE_OVERLAY.y1,
        ),
    )

    lines = build_oggetto_privacy_lines(pratica)
    baseline_y = (
        separator_y
        + (OGGETTO_GAP_AFTER_SEPARATOR_MM / 10) * CM
        + OGGETTO_FONT_SIZE
    )

    detail_lines = [lines["tipo_oggetto_line"]]
    if lines["peso_line"]:
        detail_lines.append(lines["peso_line"])
    detail_lines.append(lines["tipo_metallo_line"])

    for text in detail_lines:
        page.insert_text(
            (LEFT_MARGIN, baseline_y),
            text,
            fontsize=OGGETTO_FONT_SIZE,
            fontname="helv",
        )
        baseline_y += OGGETTO_LINE_HEIGHT

    descrizione = lines["descrizione"]
    page.insert_text(
        (LEFT_MARGIN, baseline_y),
        "Descrizione:",
        fontsize=OGGETTO_FONT_SIZE,
        fontname="helv",
    )
    if descrizione:
        prefix_font = fitz.Font("helv")
        prefix_width = prefix_font.text_length(
            "Descrizione: ",
            fontsize=OGGETTO_FONT_SIZE,
        )
        desc_top = baseline_y - OGGETTO_FONT_SIZE
        desc_rect = fitz.Rect(
            LEFT_MARGIN + prefix_width,
            desc_top,
            OGGETTO_TEXT_RIGHT,
            desc_top + OGGETTO_DESCRIZIONE_MAX_HEIGHT,
        )
        remaining = page.insert_textbox(
            desc_rect,
            descrizione,
            fontsize=OGGETTO_FONT_SIZE,
            fontname="helv",
            align=fitz.TEXT_ALIGN_LEFT,
        )
        if remaining >= 0:
            baseline_y = desc_rect.y1 - remaining + 4
        else:
            baseline_y = desc_rect.y1 + 2
    else:
        baseline_y += OGGETTO_LINE_HEIGHT

    photo_paths = _get_pratica_foto_paths(pratica, limit=2)
    content_bottom = baseline_y
    if photo_paths:
        photo_top = baseline_y + (OGGETTO_PHOTO_GAP_AFTER_TEXT_MM / 10) * CM
        photo_left = LEFT_MARGIN
        photo_bottom = photo_top
        for path in photo_paths:
            image = Image.open(path)
            img_width, img_height = image.size
            slot = fitz.Rect(
                photo_left,
                photo_top,
                photo_left + OGGETTO_PHOTO_MAX_WIDTH,
                photo_top + OGGETTO_PHOTO_MAX_HEIGHT,
            )
            rect = _fit_image_rect(slot, img_width, img_height)
            page.insert_image(rect, filename=str(path))
            photo_left = rect.x1 + OGGETTO_PHOTO_GAP
            photo_bottom = max(photo_bottom, rect.y1)
        content_bottom = photo_bottom

    return content_bottom


def _insert_foto_separator(page, content_bottom):
    separator_y = (
        content_bottom
        + (OGGETTO_AFTER_PHOTOS_SEPARATOR_GAP_MM / 10) * CM
    )
    page.draw_line(
        fitz.Point(LEFT_MARGIN, separator_y),
        fitz.Point(OGGETTO_AFTER_PHOTOS_SEPARATOR_RIGHT, separator_y),
        color=(0, 0, 0),
        width=OGGETTO_AFTER_PHOTOS_SEPARATOR_WIDTH,
    )
    return separator_y


def _insert_firma_beside_dichiarazione(page):
    """Blocco Firma a destra, allineato verticalmente alla dichiarazione."""
    firma_label = "Firma"
    label_width = fitz.Font("helv").text_length(
        firma_label,
        fontsize=FIRMA_LABEL_FONT_SIZE,
    )
    line_left = FIRMA_SIGNATURE_LINE_LEFT
    line_right = FIRMA_SIGNATURE_LINE_RIGHT
    line_center_x = (line_left + line_right) / 2

    page.insert_text(
        (line_center_x - label_width / 2, FIRMA_LABEL_BASELINE_Y),
        firma_label,
        fontsize=FIRMA_LABEL_FONT_SIZE,
        fontname="helv",
    )
    page.draw_line(
        fitz.Point(line_left, FIRMA_LINE_Y),
        fitz.Point(line_right, FIRMA_LINE_Y),
        color=(0, 0, 0),
        width=FIRMA_SIGNATURE_LINE_WIDTH,
    )
    return FIRMA_LINE_Y


def _format_privacy_indirizzo(azienda):
    parts = []
    street = " ".join(
        part.strip()
        for part in [azienda.indirizzo, azienda.civico]
        if (part or "").strip()
    )
    if street:
        parts.append(street)
    if (azienda.cap or "").strip():
        parts.append(azienda.cap.strip())
    if (azienda.comune or "").strip():
        parts.append(azienda.comune.strip())
    parts.append("ITALIA")
    return " - ".join(parts)


def _format_privacy_sito_web(azienda):
    sito_web = (azienda.sito_web or "").strip()
    if not sito_web:
        return ""
    if sito_web.startswith("https://"):
        return sito_web[8:]
    if sito_web.startswith("http://"):
        return sito_web[7:]
    return sito_web


def build_azienda_lines(azienda, first_baseline_y=None):
    baseline_y = first_baseline_y if first_baseline_y is not None else AZIENDA_FIRST_BASELINE_Y
    telefono = (azienda.telefono or "").strip()
    if telefono and not telefono.lower().startswith("tel"):
        telefono = f"Tel. {telefono}"

    partita_iva = (azienda.partita_iva or "").strip()
    if partita_iva and not partita_iva.lower().startswith("p."):
        partita_iva = f"P. Iva {partita_iva}"

    contatti = []
    sito_web = _format_privacy_sito_web(azienda)
    email = (azienda.email or "").strip()
    if sito_web:
        contatti.append(sito_web)
    if email:
        contatti.append(email)

    specs = [
        ((azienda.ragione_sociale or "").strip(), AZIENDA_RAGIONE_SOCIALE_FONT_SIZE, "hebo"),
        (_format_privacy_indirizzo(azienda), AZIENDA_LINE_FONT_SIZE, "helv"),
        (telefono, AZIENDA_LINE_FONT_SIZE, "helv"),
        (partita_iva, AZIENDA_LINE_FONT_SIZE, "helv"),
        (" - ".join(contatti), AZIENDA_LINE_FONT_SIZE, "helv"),
    ]

    lines = []
    for index, (text, fontsize, fontname) in enumerate(specs):
        if not text:
            continue
        lines.append(
            (
                text,
                fontsize,
                fontname,
                baseline_y + index * AZIENDA_LINE_HEIGHT,
            )
        )
    return lines


def build_default_privacy_testo_diritti(azienda):
    ragione_sociale = (azienda.ragione_sociale or "Azienda").strip()
    lines = [
        (
            "Per esercitare i diritti previsti all'art. 7 del Codice in materia di protezione "
            f"dei dati personali, sopra elencati, l'interessato dovrà rivolgere richiesta scritta "
            f"all'Azienda {ragione_sociale}"
        ),
    ]

    contatti = []
    indirizzo = (azienda.indirizzo_completo or "").strip()
    telefono = (azienda.telefono or "").strip()
    email = (azienda.email or "").strip()
    if indirizzo:
        contatti.append(indirizzo)
    if telefono:
        contatti.append(f"Tel {telefono}")
    if email:
        contatti.append(f"E-mail: {email}")
    if contatti:
        lines.append(", ".join(contatti))

    lines.append("C/A del Responsabile del trattamento dati.")
    return "\n".join(lines)


def get_privacy_testo_diritti_for_print(azienda):
    from apps.core.programma import get_privacy_testo_diritti

    testo = get_privacy_testo_diritti()
    if testo:
        return testo
    return build_default_privacy_testo_diritti(azienda)


def get_privacy_testo_dichiarazione_for_print():
    from apps.core.programma import get_privacy_testo_dichiarazione

    testo = get_privacy_testo_dichiarazione()
    if testo:
        return testo
    return PRIVACY_DICHIARAZIONE_DEFAULT


def _insert_dichiarazione_block(page):
    testo = get_privacy_testo_dichiarazione_for_print()
    _redact_area(page, PRIVACY_DICHIARAZIONE_TEMPLATE_OVERLAY)
    _redact_area(page, PRIVACY_DICHIARAZIONE_OVERLAY)
    if not testo:
        return
    page.insert_textbox(
        PRIVACY_DICHIARAZIONE_AREA,
        " ".join(testo.split()),
        fontsize=PRIVACY_DICHIARAZIONE_FONT_SIZE,
        fontname="helv",
        align=fitz.TEXT_ALIGN_LEFT,
    )


def _insert_diritti_block(page, azienda):
    testo = get_privacy_testo_diritti_for_print(azienda)
    if not testo and not PRIVACY_DIRITTI_TITLE:
        return

    _redact_area(page, PRIVACY_DIRITTI_TEMPLATE_OVERLAY)
    _redact_area(page, PRIVACY_DIRITTI_OVERLAY)

    title_width = fitz.Font("hebo").text_length(
        PRIVACY_DIRITTI_TITLE,
        fontsize=PRIVACY_DIRITTI_TITLE_FONT_SIZE,
    )
    page_center_x = (page.rect.x0 + page.rect.x1) / 2
    page.insert_text(
        (page_center_x - title_width / 2, PRIVACY_DIRITTI_TITLE_BASELINE_Y),
        PRIVACY_DIRITTI_TITLE,
        fontsize=PRIVACY_DIRITTI_TITLE_FONT_SIZE,
        fontname="hebo",
    )

    if not testo:
        return

    page.insert_textbox(
        PRIVACY_DIRITTI_TEXT_AREA,
        " ".join(part.strip() for part in testo.splitlines() if part.strip()),
        fontsize=PRIVACY_DIRITTI_FONT_SIZE,
        fontname="helv",
        align=fitz.TEXT_ALIGN_LEFT,
    )


def _insert_accettazione_firma_block(page):
    _redact_area(page, PRIVACY_TEMPLATE_LEFTOVER_DICHIARAZIONE_OVERLAY)
    _redact_area(page, PRIVACY_TEMPLATE_ACCETTAZIONE_OVERLAY)

    label = ACCETTAZIONE_LABEL
    label_width = fitz.Font("hebo").text_length(
        label,
        fontsize=ACCETTAZIONE_LABEL_FONT_SIZE,
    )
    line_left = ACCETTAZIONE_LINE_LEFT
    line_right = ACCETTAZIONE_LINE_RIGHT
    center_x = (line_left + line_right) / 2

    page.insert_text(
        (center_x - label_width / 2, ACCETTAZIONE_LABEL_BASELINE_Y),
        label,
        fontsize=ACCETTAZIONE_LABEL_FONT_SIZE,
        fontname="hebo",
    )

    line_y = (
        ACCETTAZIONE_LABEL_BASELINE_Y
        + (ACCETTAZIONE_LINE_GAP_MM / 10) * CM
    )
    page.draw_line(
        fitz.Point(line_left, line_y),
        fitz.Point(line_right, line_y),
        color=(0, 0, 0),
        width=ACCETTAZIONE_LINE_WIDTH,
    )
    return line_y


def _resolve_privacy_localita(pratica):
    codice = (pratica.codice or "").strip().upper()
    if codice:
        letter = codice[0]
        if letter in CODICE_LETTER_LOCALITA:
            return CODICE_LETTER_LOCALITA[letter]

    from apps.core.negozi import normalize_negozio_code

    negozio = normalize_negozio_code(pratica.negozio)
    return NEGOZIO_LOCALITA.get(negozio, "")


def build_privacy_data_line(pratica):
    localita = _resolve_privacy_localita(pratica)
    data = timezone.localdate().strftime("%d/%m/%y")
    if localita:
        return f"Data {localita} {data}"
    return f"Data {data}"


def _insert_data_block(page, pratica):
    _redact_area(page, PRIVACY_DATA_TEMPLATE_OVERLAY)
    _redact_area(page, PRIVACY_DATA_OVERLAY)
    page.insert_text(
        (LEFT_MARGIN, PRIVACY_DATA_BASELINE_Y),
        build_privacy_data_line(pratica),
        fontsize=PRIVACY_DATA_FONT_SIZE,
        fontname="helv",
    )


def _insert_ritiro_firma_block(page):
    line_left = RITIRO_FIRMA_LINE_LEFT
    line_right = RITIRO_FIRMA_LINE_RIGHT
    center_x = (line_left + line_right) / 2
    font = fitz.Font("helv")

    title_width = fitz.Font("hebo").text_length(
        RITIRO_FIRMA_TITLE,
        fontsize=RITIRO_FIRMA_FONT_SIZE,
    )
    page.insert_text(
        (center_x - title_width / 2, RITIRO_FIRMA_TITLE_BASELINE_Y),
        RITIRO_FIRMA_TITLE,
        fontsize=RITIRO_FIRMA_FONT_SIZE,
        fontname="hebo",
    )

    data_width = font.text_length(
        RITIRO_FIRMA_DATA_LABEL,
        fontsize=RITIRO_FIRMA_FONT_SIZE,
    )
    page.insert_text(
        (center_x - data_width / 2, RITIRO_FIRMA_DATA_BASELINE_Y),
        RITIRO_FIRMA_DATA_LABEL,
        fontsize=RITIRO_FIRMA_FONT_SIZE,
        fontname="helv",
    )

    page.draw_line(
        fitz.Point(line_left, RITIRO_FIRMA_LINE_Y),
        fitz.Point(line_right, RITIRO_FIRMA_LINE_Y),
        color=(0, 0, 0),
        width=RITIRO_FIRMA_LINE_WIDTH,
    )


def _redact_area(page, area):
    page.add_redact_annot(area, fill=(1, 1, 1))
    page.apply_redactions()


def _build_barcode_image(codice):
    buffer = io.BytesIO()
    Code39(codice, writer=ImageWriter(), add_checksum=False).write(
        buffer,
        options={
            "module_width": 0.28,
            "module_height": 10,
            "quiet_zone": 0.05,
            "write_text": False,
            "dpi": 300,
        },
    )
    buffer.seek(0)
    return buffer.read()


def _barcode_image_rect(area, img_bytes):
    image = Image.open(io.BytesIO(img_bytes))
    img_width, img_height = image.size
    scale = min(area.width / img_width, area.height / img_height)
    width = img_width * scale
    height = img_height * scale
    x0 = area.x1 - width
    y0 = area.y0 + (area.height - height) / 2
    return fitz.Rect(x0, y0, x0 + width, y0 + height)


def _prepare_logo_bytes(logo_bytes):
    image = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = pixels[x, y]
            if red >= 245 and green >= 245 and blue >= 245:
                pixels[x, y] = (red, green, blue, 0)

    bbox = image.getbbox()
    if bbox:
        image = image.crop(bbox)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _logo_image_rect(logo_bytes, left, top, max_width, max_height):
    image = Image.open(io.BytesIO(logo_bytes))
    img_width, img_height = image.size
    scale = min(max_width / img_width, max_height / img_height)
    width = img_width * scale
    height = img_height * scale
    return fitz.Rect(left, top, left + width, top + height)


def _svg_to_png_bytes(svg_bytes):
    doc = fitz.open(stream=svg_bytes, filetype="svg")
    pixmap = doc[0].get_pixmap(alpha=True, dpi=300)
    doc.close()
    return pixmap.tobytes("png")


def _load_azienda_logo_bytes(azienda):
    if not azienda.logo:
        return None

    logo_path = Path(azienda.logo.path)
    if not logo_path.is_file():
        return None

    logo_bytes = logo_path.read_bytes()
    if logo_path.suffix.lower() == ".svg":
        return _svg_to_png_bytes(logo_bytes)
    return logo_bytes


def _insert_title_block(page):
    _redact_area(page, PRIVACY_TITLE_TEMPLATE_OVERLAY)
    font = fitz.Font("hebo")
    text_width = font.text_length(PRIVACY_TITLE_TEXT, fontsize=PRIVACY_TITLE_FONT_SIZE)
    page.insert_text(
        (PRIVACY_TITLE_CENTER_X - text_width / 2, PRIVACY_TITLE_BASELINE_Y),
        PRIVACY_TITLE_TEXT,
        fontsize=PRIVACY_TITLE_FONT_SIZE,
        fontname="hebo",
    )


def _azienda_baseline_after_logo(logo_bottom):
    return logo_bottom + (AZIENDA_CLEAR_GAP_MM / 10) * CM + AZIENDA_RAGIONE_SOCIALE_FONT_SIZE


def _insert_logo_block(page, azienda):
    _redact_area(page, PRIVACY_LOGO_TEMPLATE_OVERLAY)

    logo_bytes = _load_azienda_logo_bytes(azienda)
    if not logo_bytes:
        return None

    prepared_logo = _prepare_logo_bytes(logo_bytes)
    logo_rect = _logo_image_rect(
        prepared_logo,
        PRIVACY_LOGO_LEFT,
        PRIVACY_LOGO_TOP,
        PRIVACY_LOGO_MAX_WIDTH,
        PRIVACY_LOGO_MAX_HEIGHT,
    )
    page.insert_image(logo_rect, stream=prepared_logo)
    return logo_rect.y1


def _insert_azienda_block(page, azienda, first_baseline_y=None):
    for text, fontsize, fontname, baseline_y in build_azienda_lines(
        azienda,
        first_baseline_y=first_baseline_y,
    ):
        page.insert_text(
            (AZIENDA_LEFT, baseline_y),
            text,
            fontsize=fontsize,
            fontname=fontname,
        )


def _insert_codice_block(page, codice):
    font = fitz.Font("hebo")
    text_width = font.text_length(codice, fontsize=CODE_TEXT_FONT_SIZE)
    page.insert_text(
        (CODE_TEXT_RIGHT - text_width, CODE_TEXT_BASELINE_Y),
        codice,
        fontsize=CODE_TEXT_FONT_SIZE,
        fontname="hebo",
    )

    barcode_bytes = _build_barcode_image(codice)
    page.insert_image(
        _barcode_image_rect(CODE_BARCODE_AREA, barcode_bytes),
        stream=barcode_bytes,
    )


def _insert_header_separator_line(page):
    _redact_area(page, HEADER_SEPARATOR_TEMPLATE_OVERLAY)
    page.draw_line(
        fitz.Point(LEFT_MARGIN, HEADER_SEPARATOR_Y),
        fitz.Point(HEADER_SEPARATOR_RIGHT, HEADER_SEPARATOR_Y),
        color=(0, 0, 0),
        width=0.1,
    )


def _apply_a4_print_defaults(doc):
    for page in doc:
        page.set_mediabox(A4_RECT)
        page.set_cropbox(A4_RECT)

    catalog_xref = doc.pdf_catalog()
    doc.xref_set_key(
        catalog_xref,
        "ViewerPreferences",
        "<< /PrintScaling /None >>",
    )


def build_privacy_pdf_bytes(pratica):
    template_path = get_privacy_pdf_path()
    if not template_path.is_file():
        raise FileNotFoundError("Modello scheda privacy non trovato.")

    codice = (pratica.codice or "").strip()
    if not codice:
        raise ValueError("Codice riparazione mancante.")

    azienda = get_default_azienda()
    if not azienda:
        raise ValueError("Nessuna azienda configurata.")

    doc = fitz.open(str(template_path))
    page = doc[0]
    _redact_area(page, PRIVACY_AZIENDA_OVERLAY)
    _insert_title_block(page)
    logo_bottom = _insert_logo_block(page, azienda)
    if logo_bottom is not None:
        azienda_baseline = _azienda_baseline_after_logo(logo_bottom)
    else:
        azienda_baseline = None

    _insert_azienda_block(page, azienda, first_baseline_y=azienda_baseline)
    _insert_header_separator_line(page)
    separator_y = _insert_cliente_block(page, pratica)
    content_bottom = _insert_oggetto_block(page, pratica, separator_y)
    _insert_foto_separator(page, content_bottom)
    _redact_area(page, PRIVACY_CODE_OVERLAY)
    _insert_codice_block(page, codice)
    _redact_area(page, PRIVACY_TEMPLATE_MID_SEPARATOR_OVERLAY)
    _redact_area(page, PRIVACY_TEMPLATE_FIRMA_LABEL_OVERLAY)
    _redact_area(page, PRIVACY_PREZZO_PAGAMENTO_OVERLAY)
    _insert_dichiarazione_block(page)
    _insert_diritti_block(page, azienda)
    _insert_accettazione_firma_block(page)
    _insert_firma_beside_dichiarazione(page)
    _insert_data_block(page, pratica)
    _insert_ritiro_firma_block(page)

    _apply_a4_print_defaults(doc)
    buffer = io.BytesIO()
    doc.save(buffer)
    doc.close()
    buffer.seek(0)
    return buffer.getvalue()


def privacy_pdf_filename(pratica):
    codice = (pratica.codice or "riparazione").replace("/", "-")
    return f"Scheda_Privacy_{codice}.pdf"


def privacy_pdf_pages_as_png_data_uris(pdf_bytes, dpi=150):
    """Rasterizza il PDF in immagini per stampare senza URL del sito in Chrome."""
    import base64

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        pages = []
        for page in doc:
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            png_bytes = pix.tobytes("png")
            pages.append(
                "data:image/png;base64," + base64.b64encode(png_bytes).decode("ascii")
            )
        return pages
    finally:
        doc.close()
