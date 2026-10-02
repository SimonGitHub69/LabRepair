"""Generazione PDF Documento di Trasporto (layout stile gestionale Centro Orafo)."""

from __future__ import annotations

import os
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

import fitz
from django.contrib.staticfiles import finders

from apps.core.negozi import normalize_negozio_code
from apps.pratiche.privacy import get_default_azienda

DDT_LOGO_STATIC = "securtek/img/ddt_header_logo.png"
ROWS_PER_PAGE = 28
ROW_HEIGHT = 15.0
TABLE_TOP = 185.0
PAGE_WIDTH = 595.32
PAGE_HEIGHT = 841.92
LEFT = 18.0
RIGHT = 557.9
# Linee: riquadri esterni più netti, griglia tabella più leggera.
LINE_W = 0.65
LINE_COLOR = (0.0, 0.0, 0.0)
GRID_W = 0.35
GRID_COLOR = (0.45, 0.45, 0.45)
BOX_W = 0.75
BOX_COLOR = (0.15, 0.15, 0.15)
CONTENT_OFFSET_Y_MM = 2
CONTENT_OFFSET_Y = CONTENT_OFFSET_Y_MM * 72 / 25.4
# Abbassa solo il riquadro "Destinazione merce".
DESTINAZIONE_OFFSET_Y_MM = 0.75
DESTINAZIONE_OFFSET_Y = DESTINAZIONE_OFFSET_Y_MM * 72 / 25.4
# Raster di backup (~300 dpi) se serve anteprima PNG.
PRINT_PNG_DPI = 300

# Tipografia
FS_LABEL = 7.5
FS_BODY = 9.0
FS_BODY_SM = 8.5
FS_TITLE = 10.0
FS_META = 10.0
FS_TABLE = 9.0
FS_TABLE_HDR = 8.0
FS_AZIENDA = 9.5
FS_AZIENDA_TITLE = 11.0


def ddt_pdf_filename(ddt):
    safe = str(ddt.numero_display).replace("/", "-")
    return f"DDT_{safe}.pdf"


def _resolve_static(path):
    found = finders.find(path)
    if found:
        return Path(found)
    return None


@lru_cache(maxsize=1)
def _system_font_paths():
    """Preferisce Arial (Windows) per testo nitido in stampa."""
    candidates = [
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts",
        Path("/usr/share/fonts/truetype/dejavu"),
        Path("/usr/share/fonts/truetype/liberation"),
        Path("/Library/Fonts"),
        Path("/System/Library/Fonts/Supplemental"),
    ]
    regular_names = (
        "arial.ttf",
        "Arial.ttf",
        "DejaVuSans.ttf",
        "LiberationSans-Regular.ttf",
        "Helvetica.ttc",
    )
    bold_names = (
        "arialbd.ttf",
        "Arial Bold.ttf",
        "ArialBD.ttf",
        "DejaVuSans-Bold.ttf",
        "LiberationSans-Bold.ttf",
    )
    regular = bold = None
    for folder in candidates:
        if not folder.exists():
            continue
        if regular is None:
            for name in regular_names:
                path = folder / name
                if path.exists():
                    regular = path
                    break
        if bold is None:
            for name in bold_names:
                path = folder / name
                if path.exists():
                    bold = path
                    break
        if regular and bold:
            break
    if regular and not bold:
        bold = regular
    return regular, bold


def _format_date(value):
    if not value:
        return ""
    return value.strftime("%d/%m/%Y")


def _format_qty(value):
    amount = Decimal(value or 0)
    return f"{amount:.2f}".replace(".", ",")


def _format_peso(value):
    if value is None:
        return ""
    amount = Decimal(value)
    if amount == 0:
        return ""
    return f"{amount:.2f}".replace(".", ",")


def _oy(y):
    return y + CONTENT_OFFSET_Y


def _pt(value):
    return round(float(value), 2)


def _draw_rect(page, rect, width=BOX_W, color=BOX_COLOR):
    x0, y0, x1, y1 = rect
    shape = page.new_shape()
    shape.draw_rect(fitz.Rect(_pt(x0), _pt(_oy(y0)), _pt(x1), _pt(_oy(y1))))
    shape.finish(color=color, width=width, stroke_opacity=1, fill=None)
    shape.commit()


def _draw_line(page, p1, p2, width=LINE_W, color=LINE_COLOR):
    shape = page.new_shape()
    shape.draw_line(
        fitz.Point(_pt(p1[0]), _pt(_oy(p1[1]))),
        fitz.Point(_pt(p2[0]), _pt(_oy(p2[1]))),
    )
    shape.finish(color=color, width=width, stroke_opacity=1, fill=None)
    shape.commit()


def _ensure_fonts(page, font_state):
    """Registra Arial/DejaVu sulla pagina; fallback helv/hebo."""
    if font_state.get("ready"):
        return font_state
    regular_path, bold_path = _system_font_paths()
    regular_name = "helv"
    bold_name = "hebo"
    try:
        if regular_path:
            regular_name = page.insert_font(fontname="ddtreg", fontfile=str(regular_path))
            # insert_font may return None; use explicit name
            regular_name = "ddtreg"
        if bold_path:
            page.insert_font(fontname="ddtbold", fontfile=str(bold_path))
            bold_name = "ddtbold"
        elif regular_path:
            bold_name = regular_name
    except Exception:
        regular_name, bold_name = "helv", "hebo"
    font_state["regular"] = regular_name
    font_state["bold"] = bold_name
    font_state["ready"] = True
    return font_state


def _text_width(text, fontsize, fontname, fontfile=None):
    value = str(text or "")
    if not value:
        return 0.0
    try:
        if fontfile:
            return fitz.get_text_length(value, fontname="f0", fontsize=fontsize, fontfile=fontfile)
        return fitz.get_text_length(value, fontname=fontname, fontsize=fontsize)
    except Exception:
        return len(value) * fontsize * 0.5


def _insert_text(page, point, text, *, fontsize=FS_BODY, bold=False, font_state=None, color=(0, 0, 0)):
    if not text:
        return 0.0
    font_state = font_state or {}
    _ensure_fonts(page, font_state)
    name = font_state["bold"] if bold else font_state["regular"]
    value = str(text)
    page.insert_text(
        fitz.Point(_pt(point[0]), _pt(_oy(point[1]))),
        value,
        fontsize=fontsize,
        fontname=name,
        color=color,
    )
    regular_path, bold_path = _system_font_paths()
    fontfile = bold_path if bold and bold_path else regular_path
    return _text_width(value, fontsize, name, fontfile=str(fontfile) if fontfile else None)


def _insert_text_right(page, right_x, baseline_y, text, *, fontsize=FS_BODY, bold=False, font_state=None):
    if not text:
        return
    font_state = font_state or {}
    _ensure_fonts(page, font_state)
    name = font_state["bold"] if bold else font_state["regular"]
    value = str(text)
    regular_path, bold_path = _system_font_paths()
    fontfile = bold_path if bold and bold_path else regular_path
    width = _text_width(value, fontsize, name, fontfile=str(fontfile) if fontfile else None)
    _insert_text(
        page,
        (right_x - width, baseline_y),
        value,
        fontsize=fontsize,
        bold=bold,
        font_state=font_state,
    )


def _azienda_lines(azienda):
    if not azienda:
        return []

    lines = []
    ragione = (azienda.ragione_sociale or "").strip()
    if ragione:
        lines.append((ragione, True, FS_AZIENDA_TITLE))

    street = " ".join(part for part in [azienda.indirizzo, azienda.civico] if part).strip()
    city_bits = [part for part in [azienda.cap, azienda.comune] if part]
    city = " ".join(city_bits)
    if azienda.provincia:
        city = f"{city} ({azienda.provincia})" if city else f"({azienda.provincia})"
    location = " · ".join(part for part in [street, city, "Italia"] if part)
    if location:
        lines.append((location, False, FS_AZIENDA))

    extras = []
    if azienda.telefono:
        extras.append(f"Tel. {azienda.telefono}")
    if azienda.partita_iva:
        extras.append(f"P.IVA {azienda.partita_iva}")
    if extras:
        lines.append((" · ".join(extras), False, FS_BODY_SM))

    web_mail = " · ".join(
        part for part in [(azienda.sito_web or "").strip(), (azienda.email or "").strip()] if part
    )
    if web_mail:
        lines.append((web_mail, False, FS_BODY_SM))
    return lines


def _get_negozio_for_ddt(ddt):
    code = normalize_negozio_code(getattr(ddt, "negozio", None))
    if not code:
        return None
    try:
        from apps.core.models import Negozio

        return (
            Negozio.objects.filter(is_active=True, codice=code)
            .only(
                "codice",
                "denominazione",
                "indirizzo",
                "civico",
                "cap",
                "comune",
                "provincia",
            )
            .first()
        )
    except Exception:
        return None


def _negozio_sede_lines(negozio):
    if not negozio:
        return []
    sede = (negozio.sede_operativa or "").strip()
    if not sede:
        return []
    denominazione = (negozio.denominazione or "").strip()
    title = f"Sede operativa — {denominazione}" if denominazione else "Sede operativa"
    return [(title, True, FS_BODY), (sede, False, FS_BODY_SM)]


def _load_logo_stream(azienda):
    if azienda and azienda.logo:
        try:
            with azienda.logo.open("rb") as handle:
                data = handle.read()
            if data:
                return data
        except OSError:
            pass

    path = _resolve_static(DDT_LOGO_STATIC)
    if path and path.exists():
        return path.read_bytes()
    return None


def _draw_form_frame(page, *, page_index, page_count, font_state):
    # Recipient boxes
    _draw_rect(page, (280, 10, RIGHT, 75))
    _draw_rect(page, (280, 77 + DESTINAZIONE_OFFSET_Y, RIGHT, 142 + DESTINAZIONE_OFFSET_Y))
    _insert_text(page, (287, 22), "Spett.le", fontsize=FS_LABEL, bold=True, font_state=font_state)
    _insert_text(
        page,
        (287, 89 + DESTINAZIONE_OFFSET_Y),
        "Destinazione merce",
        fontsize=FS_LABEL,
        bold=True,
        font_state=font_state,
    )

    # Meta bar
    _draw_rect(page, (LEFT, 149, RIGHT, 186))
    _draw_line(page, (362, 149), (362, 186), width=LINE_W)
    _draw_line(page, (LEFT, 167), (362, 167), width=LINE_W)
    _draw_line(page, (94, 167), (94, 186), width=LINE_W)
    _insert_text(
        page,
        (21, 160),
        "DOC. TRASPORTO CLIENTE N.",
        fontsize=FS_LABEL,
        bold=True,
        font_state=font_state,
    )
    _insert_text(page, (216.5, 160), "del", fontsize=FS_LABEL, bold=True, font_state=font_state)
    _insert_text(page, (313.2, 160), "pag.", fontsize=FS_LABEL, bold=True, font_state=font_state)
    _insert_text(page, (21, 178), "Cod. Cli.", fontsize=FS_LABEL, bold=True, font_state=font_state)
    _insert_text(page, (97, 178), "Agente", fontsize=FS_LABEL, bold=True, font_state=font_state)
    _insert_text(page, (367, 160), "Partita IVA", fontsize=FS_LABEL, bold=True, font_state=font_state)
    _insert_text(page, (367, 178), "Cod. Fiscale", fontsize=FS_LABEL, bold=True, font_state=font_state)

    table_bottom = TABLE_TOP + ROW_HEIGHT * (ROWS_PER_PAGE + 1)
    _draw_rect(page, (LEFT, TABLE_TOP, RIGHT, table_bottom), width=BOX_W, color=BOX_COLOR)
    for x in (94.0, 492.0, 514.0):
        _draw_line(page, (x, TABLE_TOP), (x, table_bottom), width=GRID_W, color=GRID_COLOR)
    for i in range(1, ROWS_PER_PAGE + 1):
        y = TABLE_TOP + ROW_HEIGHT * i
        # Prima riga sotto header un filo più marcata; le altre più leggere.
        w = LINE_W if i == 1 else GRID_W
        c = LINE_COLOR if i == 1 else GRID_COLOR
        _draw_line(page, (LEFT, y), (RIGHT, y), width=w, color=c)

    _insert_text(
        page, (38, TABLE_TOP + 10.5), "Articolo", fontsize=FS_TABLE_HDR, bold=True, font_state=font_state
    )
    _insert_text(
        page,
        (250, TABLE_TOP + 10.5),
        "Descrizione",
        fontsize=FS_TABLE_HDR,
        bold=True,
        font_state=font_state,
    )
    _insert_text(
        page, (496, TABLE_TOP + 10.5), "UM", fontsize=FS_TABLE_HDR, bold=True, font_state=font_state
    )
    _insert_text(
        page, (528, TABLE_TOP + 10.5), "Qtà", fontsize=FS_TABLE_HDR, bold=True, font_state=font_state
    )

    _draw_rect(page, (LEFT, 639, RIGHT, 739))
    _draw_line(page, (LEFT, 655), (RIGHT, 655), width=LINE_W)
    _draw_line(page, (LEFT, 672), (RIGHT, 672), width=LINE_W)
    _draw_line(page, (LEFT, 689), (RIGHT, 689), width=LINE_W)
    _draw_line(page, (288, 639), (288, 689), width=LINE_W)
    _insert_text(page, (21, 649), "Causale", fontsize=FS_LABEL, bold=True, font_state=font_state)
    _insert_text(page, (291, 649), "Aspetto Beni", fontsize=FS_LABEL, bold=True, font_state=font_state)
    _insert_text(page, (21, 666), "Trasporto a cura", fontsize=FS_LABEL, bold=True, font_state=font_state)
    _insert_text(page, (291, 666), "Peso lordo (kg)", fontsize=FS_LABEL, bold=True, font_state=font_state)
    _insert_text(page, (501, 666), "Colli", fontsize=FS_LABEL, bold=True, font_state=font_state)
    _insert_text(page, (21, 683), "Vettore", fontsize=FS_LABEL, bold=True, font_state=font_state)
    _insert_text(
        page, (291, 683), "Data Inizio Trasporto", fontsize=FS_LABEL, bold=True, font_state=font_state
    )
    _insert_text(page, (451, 683), "Ora", fontsize=FS_LABEL, bold=True, font_state=font_state)
    _insert_text(page, (21, 700), "Note", fontsize=FS_LABEL, bold=True, font_state=font_state)

    _draw_rect(page, (LEFT, 739, RIGHT, 776))
    _draw_line(page, (288, 739), (288, 776), width=LINE_W)
    _insert_text(
        page, (21, 751), "Firma Conducente", fontsize=FS_LABEL, bold=True, font_state=font_state
    )
    _insert_text(
        page, (291, 751), "Firma Destinatario", fontsize=FS_LABEL, bold=True, font_state=font_state
    )

    _ = page_index, page_count


def _insert_header(page, azienda, ddt, negozio=None, font_state=None):
    font_state = font_state or {}
    logo = _load_logo_stream(azienda)
    if logo:
        page.insert_image(
            fitz.Rect(18, _oy(8), 268, _oy(48)),
            stream=logo,
            keep_proportion=True,
        )

    y = 60
    for text, bold, size in _azienda_lines(azienda):
        _insert_text(page, (18, y), text, fontsize=size, bold=bold, font_state=font_state)
        y += 11 if bold else 10

    for text, bold, size in _negozio_sede_lines(negozio):
        if y > 140:
            break
        y += 1
        _insert_text(page, (18, y), text, fontsize=size, bold=bold, font_state=font_state)
        y += 10

    # Destinatario
    _insert_text(
        page,
        (287, 36),
        ddt.destinatario_ragione_sociale,
        fontsize=FS_TITLE,
        bold=True,
        font_state=font_state,
    )
    _insert_text(
        page,
        (287, 49),
        ddt.destinatario_indirizzo,
        fontsize=FS_BODY,
        bold=False,
        font_state=font_state,
    )
    _insert_text(
        page,
        (287, 61),
        ddt.destinatario_citta_line,
        fontsize=FS_BODY,
        bold=False,
        font_state=font_state,
    )

    if ddt.destinazione_merce:
        dest_y = 103 + DESTINAZIONE_OFFSET_Y
        for line in str(ddt.destinazione_merce).splitlines()[:3]:
            _insert_text(
                page, (287, dest_y), line.strip(), fontsize=FS_BODY, bold=False, font_state=font_state
            )
            dest_y += 11


def _insert_meta(page, ddt, page_number, page_count, font_state=None):
    font_state = font_state or {}
    _insert_text(
        page, (168, 160), ddt.numero_display, fontsize=FS_META, bold=True, font_state=font_state
    )
    _insert_text(
        page,
        (235, 160),
        _format_date(ddt.data_documento),
        fontsize=FS_META,
        bold=True,
        font_state=font_state,
    )
    page_label = f"{page_number}/{page_count}" if page_count else str(page_number)
    _insert_text(page, (333, 160), page_label, fontsize=FS_META, bold=True, font_state=font_state)
    _insert_text(
        page,
        (70, 178),
        ddt.destinatario_codice_cliente,
        fontsize=FS_BODY,
        bold=True,
        font_state=font_state,
    )
    _insert_text(page, (130, 178), ddt.agente, fontsize=FS_BODY, bold=True, font_state=font_state)
    _insert_text(
        page,
        (420, 160),
        ddt.destinatario_partita_iva,
        fontsize=FS_BODY,
        bold=True,
        font_state=font_state,
    )
    _insert_text(
        page,
        (420, 178),
        ddt.destinatario_codice_fiscale,
        fontsize=FS_BODY,
        bold=True,
        font_state=font_state,
    )


def _insert_rows(page, rows, font_state=None):
    font_state = font_state or {}
    y = TABLE_TOP + ROW_HEIGHT
    qty_right = 555.5
    for riga in rows:
        articolo = (riga.articolo or "").strip()
        if not articolo and riga.pratica_id:
            articolo = (riga.pratica.codice or "").strip()
        descrizione = (riga.descrizione or "").strip()
        # Descrizione: evita sforo nella colonna UM
        regular_path, _ = _system_font_paths()
        fontfile = str(regular_path) if regular_path else None
        max_w = 390
        while descrizione and _text_width(descrizione, FS_TABLE, "helv", fontfile=fontfile) > max_w:
            descrizione = descrizione[:-1]
        if descrizione != (riga.descrizione or "").strip() and len(descrizione) > 1:
            descrizione = descrizione[:-1] + "…"

        _insert_text(page, (22, y + 10.5), articolo, fontsize=FS_TABLE, bold=True, font_state=font_state)
        _insert_text(
            page, (98, y + 10.5), descrizione, fontsize=FS_TABLE, bold=False, font_state=font_state
        )
        _insert_text(
            page,
            (497, y + 10.5),
            riga.unita_misura or "NR",
            fontsize=FS_TABLE,
            bold=False,
            font_state=font_state,
        )
        _insert_text_right(
            page,
            qty_right,
            y + 10.5,
            _format_qty(riga.quantita),
            fontsize=FS_TABLE,
            bold=True,
            font_state=font_state,
        )
        y += ROW_HEIGHT


def _insert_footer(page, ddt, font_state=None):
    font_state = font_state or {}
    _insert_text(page, (58, 649), ddt.causale, fontsize=FS_BODY, bold=True, font_state=font_state)
    _insert_text(page, (355, 649), ddt.aspetto_beni, fontsize=FS_BODY, bold=True, font_state=font_state)
    _insert_text(
        page, (95, 666), ddt.trasporto_a_cura, fontsize=FS_BODY, bold=True, font_state=font_state
    )
    _insert_text(
        page,
        (365, 666),
        _format_peso(ddt.peso_lordo_kg),
        fontsize=FS_BODY,
        bold=True,
        font_state=font_state,
    )
    _insert_text(page, (525, 666), str(ddt.colli or ""), fontsize=FS_BODY, bold=True, font_state=font_state)
    _insert_text(page, (58, 683), ddt.vettore, fontsize=FS_BODY, bold=True, font_state=font_state)
    _insert_text(
        page,
        (395, 683),
        _format_date(ddt.data_inizio_trasporto or ddt.data_documento),
        fontsize=FS_BODY,
        bold=True,
        font_state=font_state,
    )
    if ddt.ora_inizio_trasporto:
        _insert_text(
            page,
            (475, 683),
            ddt.ora_inizio_trasporto.strftime("%H:%M"),
            fontsize=FS_BODY,
            bold=True,
            font_state=font_state,
        )
    if ddt.note:
        note_y = 712
        for line in str(ddt.note).splitlines()[:2]:
            _insert_text(
                page, (54, note_y), line.strip(), fontsize=FS_BODY_SM, bold=False, font_state=font_state
            )
            note_y += 10


def build_ddt_pdf_bytes(ddt):
    azienda = get_default_azienda()
    negozio = _get_negozio_for_ddt(ddt)
    righe = list(ddt.righe.filter(is_active=True).select_related("pratica").order_by("ordine", "id"))
    if not righe:
        raise ValueError("Il DDT non contiene righe da stampare.")

    chunks = [righe[i : i + ROWS_PER_PAGE] for i in range(0, len(righe), ROWS_PER_PAGE)]
    page_count = len(chunks)

    doc = fitz.open()
    for page_index, chunk in enumerate(chunks, start=1):
        page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        font_state = {}
        _ensure_fonts(page, font_state)
        _draw_form_frame(page, page_index=page_index, page_count=page_count, font_state=font_state)
        _insert_header(page, azienda, ddt, negozio=negozio, font_state=font_state)
        _insert_meta(page, ddt, page_index, page_count, font_state=font_state)
        _insert_rows(page, chunk, font_state=font_state)
        _insert_footer(page, ddt, font_state=font_state)

    pdf_bytes = doc.tobytes(deflate=True, garbage=3)
    doc.close()
    return pdf_bytes


def ddt_pdf_pages_as_png_data_uris(pdf_bytes, zoom=None, dpi=None):
    import base64

    if zoom is None:
        dpi = dpi or PRINT_PNG_DPI
        zoom = dpi / 72.0

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    matrix = fitz.Matrix(zoom, zoom)
    for page in doc:
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        encoded = base64.b64encode(pix.tobytes("png")).decode("ascii")
        images.append(f"data:image/png;base64,{encoded}")
    doc.close()
    return images
