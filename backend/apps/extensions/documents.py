from io import BytesIO
from xml.sax.saxutils import escape

from docx import Document
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from apps.competitions.exporters import _register_font


def render_document(title, lines, columns, rows, file_format="pdf", qr_url=None):
    """Safe shared renderer: escape user content, repeat headers, allow page breaks.

    Formats are fictional unsigned forms until sources are verified.
    """
    stream = BytesIO()
    warning = "Демонстрационная форма. Не является приказом, решением о выплате или электронной подписью."
    if file_format == "docx":
        doc = Document()
        doc.add_paragraph(warning)
        doc.add_heading(title, 0)
        for line in lines:
            doc.add_paragraph(str(line))
        table = doc.add_table(rows=1, cols=len(columns))
        table.style = "Table Grid"
        for cell, label in zip(table.rows[0].cells, columns):
            cell.text = str(label)
        for row in rows:
            for cell, value in zip(table.add_row().cells, row):
                cell.text = str(value if value is not None else "—")
        doc.save(stream)
    else:
        _register_font()
        style = ParagraphStyle(
            "extension", fontName="FSP-DejaVu", fontSize=9, leading=14, wordWrap="CJK"
        )

        def paragraph(value):
            return Paragraph(escape(str(value if value is not None else "—")), style)

        story = [paragraph(warning), Spacer(1, 12), paragraph(title), Spacer(1, 12)]
        story += [paragraph(line) for line in lines]
        story.append(Spacer(1, 12))
        table = Table(
            [[paragraph(c) for c in columns]]
            + [[paragraph(v) for v in row] for row in rows],
            repeatRows=1,
            colWidths=[480 / len(columns)] * len(columns),
        )
        table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#221F73")),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEEDF9")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(table)
        if qr_url:
            code = QrCodeWidget(qr_url)
            bounds = code.getBounds()
            drawing = Drawing(
                100,
                100,
                transform=[
                    100 / (bounds[2] - bounds[0]),
                    0,
                    0,
                    100 / (bounds[3] - bounds[1]),
                    0,
                    0,
                ],
            )
            drawing.add(code)
            story += [Spacer(1, 12), drawing, paragraph(qr_url)]
        SimpleDocTemplate(stream, leftMargin=48, rightMargin=48).build(story)
    return stream.getvalue()
