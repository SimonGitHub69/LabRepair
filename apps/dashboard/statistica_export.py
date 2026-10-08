"""Export CSV e XLSX della statistica riparazioni."""

from __future__ import annotations

import csv
import io
import zipfile
from decimal import Decimal
from xml.sax.saxutils import escape

METRICHE_EXPORT = (
    ("numero", "Numero riparazioni", "int"),
    ("prezzo_pubblico", "Prezzo al pubblico", "money"),
    ("prezzo_pagato", "Prezzo pagato", "money"),
    ("costo_totale", "Costo totale", "money"),
)


def export_table(payload):
    series = payload["series"]
    headers = ["Periodo"]
    kinds = ["text"]
    for item in series:
        for _key, label, kind in METRICHE_EXPORT:
            headers.append(f"{item['label']} - {label}")
            kinds.append(kind)
    for _key, label, kind in METRICHE_EXPORT:
        headers.append(f"Totale - {label}")
        kinds.append(kind)

    rows = []
    for position, period in enumerate(payload["labels"]):
        row = [_safe_text(period)]
        totals = {
            "numero": 0,
            "prezzo_pubblico": Decimal("0.00"),
            "prezzo_pagato": Decimal("0.00"),
            "costo_totale": Decimal("0.00"),
        }
        for item in series:
            for key, _label, kind in METRICHE_EXPORT:
                value = _number(item[key][position], kind)
                row.append(value)
                totals[key] += value
        for key, _label, kind in METRICHE_EXPORT:
            row.append(totals[key])
        rows.append(row)

    total_row = ["Totale"]
    for index, kind in enumerate(kinds[1:], start=1):
        if kind == "int":
            total_row.append(sum(int(row[index]) for row in rows))
        else:
            total_row.append(sum((row[index] for row in rows), Decimal("0.00")))
    rows.append(total_row)
    return headers, kinds, rows


def render_csv(payload) -> bytes:
    headers, kinds, rows = export_table(payload)
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
    writer.writerow(headers)
    for row in rows:
        writer.writerow(_csv_row(row, kinds))
    return buffer.getvalue().encode("utf-8-sig")


def render_xlsx(payload) -> bytes:
    headers, kinds, rows = export_table(payload)
    sheet = _worksheet_xml(headers, kinds, rows)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _CONTENT_TYPES)
        archive.writestr("_rels/.rels", _ROOT_RELS)
        archive.writestr("xl/workbook.xml", _WORKBOOK)
        archive.writestr("xl/_rels/workbook.xml.rels", _WORKBOOK_RELS)
        archive.writestr("xl/styles.xml", _STYLES)
        archive.writestr("xl/worksheets/sheet1.xml", sheet)
    return buffer.getvalue()


def export_statistica(payload, formato):
    if (formato or "").strip().lower() == "xlsx":
        return (
            render_xlsx(payload),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "xlsx",
        )
    return render_csv(payload), "text/csv; charset=utf-8", "csv"


def _number(value, kind):
    if kind == "int":
        return int(value or 0)
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def _safe_text(value):
    text = str(value or "")
    if text[:1] in ("=", "+", "-", "@"):
        return "'" + text
    return text


def _csv_row(row, kinds):
    cells = []
    for value, kind in zip(row, kinds):
        if kind == "text":
            cells.append(value)
        elif kind == "int":
            cells.append(f"{int(value):,}".replace(",", "."))
        else:
            cells.append(f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    return cells


def _column_name(index):
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _style_id(kind, bold):
    if kind == "text":
        return "1" if bold else "0"
    if kind == "int":
        return "4" if bold else "2"
    return "5" if bold else "3"


def _cell_xml(ref, value, kind, style):
    if kind == "text":
        text = escape(str(value))
        return (
            f'<c r="{ref}" t="inlineStr" s="{style}">'
            f'<is><t xml:space="preserve">{text}</t></is></c>'
        )
    if kind == "int":
        number = str(int(value))
    else:
        number = f"{value:.2f}"
    return f'<c r="{ref}" s="{style}"><v>{number}</v></c>'


def _worksheet_xml(headers, kinds, rows):
    last_col = _column_name(len(headers))
    last_row = len(rows) + 1
    columns = []
    for index, header in enumerate(headers, start=1):
        width = min(42, max(14, len(header) + 2))
        columns.append(
            f'<col min="{index}" max="{index}" width="{width}" customWidth="1"/>'
        )

    xml_rows = []
    header_cells = []
    for index, header in enumerate(headers, start=1):
        ref = f"{_column_name(index)}1"
        header_cells.append(_cell_xml(ref, header, "text", "1"))
    xml_rows.append(f'<row r="1">{"".join(header_cells)}</row>')

    for row_index, row in enumerate(rows, start=2):
        bold = row_index == last_row
        cells = []
        for col_index, (value, kind) in enumerate(zip(row, kinds), start=1):
            ref = f"{_column_name(col_index)}{row_index}"
            cells.append(_cell_xml(ref, value, kind, _style_id(kind, bold)))
        xml_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetViews><sheetView workbookViewId=\"0\">"
        '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
        "</sheetView></sheetViews>"
        f'<dimension ref="A1:{last_col}{last_row}"/>'
        "<sheetFormatPr defaultRowHeight=\"15\"/>"
        f"<cols>{''.join(columns)}</cols>"
        f"<sheetData>{''.join(xml_rows)}</sheetData>"
        "</worksheet>"
    )


_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>
"""

_ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>
"""

_WORKBOOK = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Statistica" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>
"""

_WORKBOOK_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>
"""

_STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <numFmts count="1">
    <numFmt numFmtId="164" formatCode="#,##0.00"/>
  </numFmts>
  <fonts count="2">
    <font><sz val="11"/><name val="Calibri"/></font>
    <font><b/><sz val="11"/><name val="Calibri"/></font>
  </fonts>
  <fills count="2">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
  </fills>
  <borders count="1">
    <border><left/><right/><top/><bottom/><diagonal/></border>
  </borders>
  <cellStyleXfs count="1">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>
  </cellStyleXfs>
  <cellXfs count="6">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>
    <xf numFmtId="1" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
    <xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
    <xf numFmtId="1" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1" applyNumberFormat="1"/>
    <xf numFmtId="164" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1" applyNumberFormat="1"/>
  </cellXfs>
</styleSheet>
"""
