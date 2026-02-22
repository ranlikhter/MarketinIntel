"""
Minimal stdlib-only XLSX writer.

Generates a valid .xlsx (Office Open XML) file from a list of headers + rows
without requiring any third-party packages (openpyxl, xlsxwriter, etc.).

Usage:
    from services.xlsx_writer import write_xlsx
    data = write_xlsx("Sheet1", ["Col A", "Col B"], [["foo", 1], ["bar", 2.5]])
    # data is bytes — pass to StreamingResponse or write to file
"""

import io
import zipfile
from xml.sax.saxutils import escape as xml_escape


def _col_letter(n: int) -> str:
    """Convert 0-indexed column number to Excel column letter(s). 0→A, 25→Z, 26→AA."""
    s = ''
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def write_xlsx(sheet_name: str, headers: list, rows: list) -> bytes:
    """
    Return bytes of a valid .xlsx file.

    Args:
        sheet_name: Worksheet tab name.
        headers:    List of column header strings (first row, bold + blue).
        rows:       List of rows; each row is a list of values
                    (str | int | float | None).

    The header row is rendered with a bold white font on a blue background
    (Excel style index 1).  All other cells use the default style.
    """
    # ── 1. Build shared-string index ────────────────────────────────────────────
    str_index: dict[str, int] = {}
    shared_strings: list[str] = []

    def _ss(val) -> int:
        s = str(val) if val is not None else ''
        if s not in str_index:
            str_index[s] = len(shared_strings)
            shared_strings.append(s)
        return str_index[s]

    # ── 2. Build <row> elements ──────────────────────────────────────────────────
    all_rows = [headers] + list(rows)
    row_xml_parts: list[str] = []

    for row_num, row in enumerate(all_rows, start=1):
        is_header = row_num == 1
        cells: list[str] = []
        for col_num, val in enumerate(row):
            ref = f"{_col_letter(col_num)}{row_num}"
            if val is None or val == '':
                continue
            if isinstance(val, bool):
                # Boolean → string so it shows as True/False not 1/0
                idx = _ss(str(val))
                style = ' s="1"' if is_header else ''
                cells.append(f'<c r="{ref}" t="s"{style}><v>{idx}</v></c>')
            elif isinstance(val, (int, float)):
                style = ' s="1"' if is_header else ''
                cells.append(f'<c r="{ref}"{style}><v>{val}</v></c>')
            else:
                idx = _ss(val)
                style = ' s="1"' if is_header else ''
                cells.append(f'<c r="{ref}" t="s"{style}><v>{idx}</v></c>')
        row_xml_parts.append(f'<row r="{row_num}">{"".join(cells)}</row>')

    # ── 3. Static XML templates ──────────────────────────────────────────────────
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        '</Types>'
    )

    dot_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '</Relationships>'
    )

    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets><sheet name="{xml_escape(sheet_name)}" sheetId="1" r:id="rId1"/></sheets>'
        '</workbook>'
    )

    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>'
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        '</Relationships>'
    )

    # Bold white on blue (style 1) for header row; normal (style 0) for data
    styles_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="2">'
        '<font><sz val="11"/><name val="Calibri"/></font>'
        '<font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font>'
        '</fonts>'
        '<fills count="3">'
        '<fill><patternFill patternType="none"/></fill>'
        '<fill><patternFill patternType="gray125"/></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FF2563EB"/><bgColor indexed="64"/></patternFill></fill>'
        '</fills>'
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="2">'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/>'
        '</cellXfs>'
        '</styleSheet>'
    )

    # ── 4. Shared strings XML ────────────────────────────────────────────────────
    n = len(shared_strings)
    ss_items = ''.join(f'<si><t xml:space="preserve">{xml_escape(s)}</t></si>' for s in shared_strings)
    shared_strings_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="{n}" uniqueCount="{n}">'
        f'{ss_items}</sst>'
    )

    # ── 5. Worksheet XML ─────────────────────────────────────────────────────────
    sheet_data = ''.join(row_xml_parts)
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{sheet_data}</sheetData>'
        '</worksheet>'
    )

    # ── 6. Pack into ZIP (XLSX = ZIP) ────────────────────────────────────────────
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('[Content_Types].xml', content_types)
        zf.writestr('_rels/.rels', dot_rels)
        zf.writestr('xl/workbook.xml', workbook_xml)
        zf.writestr('xl/_rels/workbook.xml.rels', workbook_rels)
        zf.writestr('xl/styles.xml', styles_xml)
        zf.writestr('xl/sharedStrings.xml', shared_strings_xml)
        zf.writestr('xl/worksheets/sheet1.xml', sheet_xml)
    return buf.getvalue()
