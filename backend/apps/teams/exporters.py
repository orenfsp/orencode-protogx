from io import BytesIO

from docx import Document
from docx.shared import Cm, Pt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from apps.competitions.exporters import _font_path


def _rows(team):
    return list(team.memberships.filter(removed_at__isnull=True).select_related("athlete").order_by("position"))


def _title(team, draft=False):
    return ("ПРОЕКТ ОФИЦИАЛЬНОГО ПОРЯДКА" if draft else "СОСТАВ РЕГИОНАЛЬНОЙ КОМАНДЫ")


def render_team_docx(team, *, draft=False):
    doc = Document()
    section = doc.sections[0]
    section.top_margin = section.bottom_margin = Cm(1.6)
    section.left_margin = section.right_margin = Cm(1.6)
    doc.styles["Normal"].font.name = "DejaVu Sans"
    doc.styles["Normal"].font.size = Pt(10)
    doc.add_heading(_title(team, draft=draft), level=0)
    doc.add_paragraph(f"Команда: {team.name}")
    doc.add_paragraph(f"Регион: {team.region}")
    doc.add_paragraph(f"Сезон: {team.season.year}; дисциплина: {team.discipline.name}; возрастная группа: {team.age_group.name}")
    doc.add_paragraph("Документ сформирован из сохранённого состава; проект не является подписанным официальным приказом." if draft else "Дата формирования: текущая дата демонстрационной системы.")
    table = doc.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    for cell, text in zip(table.rows[0].cells, ("№", "Спортсмен", "Организация / email", "Рейтинг")):
        cell.text = text
    for index, membership in enumerate(_rows(team), 1):
        cells = table.add_row().cells
        cells[0].text = str(index)
        cells[1].text = membership.athlete.full_name
        cells[2].text = membership.athlete.email
        cells[3].text = membership.eligibility_snapshot.get("rating_score") or "—"
    doc.add_paragraph("Подпись представителя федерации: ____________________")
    stream = BytesIO()
    doc.save(stream)
    return stream.getvalue()


def render_team_pdf(team, *, draft=False):
    font_name = "FSP-DejaVu"
    if font_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(font_name, _font_path()))
    stream = BytesIO()
    doc = SimpleDocTemplate(stream, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm, title=_title(team, draft=draft), invariant=1)
    normal = ParagraphStyle("team-normal", fontName=font_name, fontSize=9, leading=13)
    heading = ParagraphStyle("team-heading", parent=normal, fontSize=16, leading=20, textColor=colors.HexColor("#221F73"), spaceAfter=8)
    story = [Paragraph(_title(team, draft=draft), heading), Paragraph(f"Команда: {team.name}", normal), Paragraph(f"Регион: {team.region}; сезон: {team.season.year}; дисциплина: {team.discipline.name}; возрастная группа: {team.age_group.name}", normal), Spacer(1, 10)]
    data = [["№", "Спортсмен", "Email", "Рейтинг"]]
    data.extend([[str(index), item.athlete.full_name, item.athlete.email, item.eligibility_snapshot.get("rating_score") or "—"] for index, item in enumerate(_rows(team), 1)])
    table = Table(data, colWidths=[12 * mm, 60 * mm, 68 * mm, 22 * mm], repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEEDF9")), ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#221F73")), ("FONTNAME", (0, 0), (-1, -1), font_name), ("FONTSIZE", (0, 0), (-1, -1), 8), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.extend([table, Spacer(1, 12), Paragraph("Проект не является подписанным официальным приказом." if draft else "Сформировано из базы данных платформы.", normal), Paragraph("Подпись представителя федерации: ____________________", normal)])
    doc.build(story)
    return stream.getvalue()
