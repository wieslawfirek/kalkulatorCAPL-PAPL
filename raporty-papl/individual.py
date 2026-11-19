import base64
import io
from pathlib import Path
from reportlab.lib.colors import white, HexColor
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from xml.sax.saxutils import escape

from branding import GREEN as TEAL, INK, MUTED, RULE as BORDER, keep_single_letters, report_frame
from feedback import child_feedback
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

W, H = 595.28, 841.89
ABBR = ('P', 'DP', 'S', 'W')
def register_font():
    if 'PAPL' not in pdfmetrics.getRegisteredFontNames():
        path = Path(__file__).with_name('font.b64')
        pdfmetrics.registerFont(TTFont('PAPL', io.BytesIO(base64.b64decode(path.read_bytes()))))

def fmt(value):
    return f'{value:,.2f}'.rstrip('0').rstrip('.').replace(',', ' ').replace('.', ',')

def report(records, norms, metrics, use_ai=True, feedback_result=None):
    register_font()
    out = io.BytesIO()
    c = Canvas(out, pagesize=(W, H))
    records = sorted(records, key=lambda r:r['turn'])
    latest = records[-1]
    keys = list(metrics)

    def text(x, y, value, size=10, color=INK, centered=False):
        c.setFont('PAPL', size)
        c.setFillColor(color)
        (c.drawCentredString if centered else c.drawString)(x, H-y, str(value))

    def rect(x, y, w, h, fill, border=None, radius=0):
        c.setFillColor(fill)
        if border:
            c.setStrokeColor(border)
        if radius:
            c.roundRect(x,H-y-h,w,h,radius,fill=1,stroke=int(bool(border)))
        else:
            c.rect(x,H-y-h,w,h,fill=1,stroke=int(bool(border)))

    def header(title,page):
        report_frame(c, W, H, page)
        text(42,67,'RAPORT INDYWIDUALNY',9,TEAL)
        text(42,94,title,20)
        metadata = f'{latest["name"]} · {latest["school"]} · klasa {latest["classroom"]} · pomiary {len(records)}'
        block(metadata, 42, 103, 511, 9, MUTED)

    def block(value, x, y, width, size, color=INK):
        style = ParagraphStyle('PAPL', fontName='PAPL', fontSize=size, leading=size*1.28, textColor=color)
        paragraph = Paragraph(escape(value), style)
        _, height = paragraph.wrap(width, H)
        paragraph.drawOn(c, x, H-y-height)
        return height

    # Category positions are deliberately independent of numerical scores.
    # Display the latest three measurements; keep all history for feedback.
    shown = records[-3:]
    palette = tuple(map(HexColor, ('#F7B4C4', '#FFE17B', '#B7E69B', '#168450')))
    navy = HexColor('#122447')
    cyan = HexColor('#E7F7FA')
    marker_colors = (HexColor('#758295'), HexColor('#1776BB'), navy)
    left, width = 32, 531
    bar_x, bar_w, table_x, table_w = 214, 184, 411, 140
    col_w = table_w / len(shown)

    def category_bar(y, metric):
        zone_w = bar_w / 4
        for level, color in enumerate(palette):
            rect(bar_x + level * zone_w, y, zone_w, 17, color)
            text(bar_x + (level + .5) * zone_w, y + 12, ABBR[level], 9,
                 white if level == 3 else navy, True)
        current = shown[-1]['levels'][metric]
        if current is not None and shown[-1]['scores'][metric] is not None:
            c.setStrokeColor(navy)
            c.setLineWidth(1.8)
            c.roundRect(bar_x + current * zone_w - 1, H-y-18,
                        zone_w + 2, 19, 3, fill=0, stroke=1)
        for level in range(4):
            group = [(i, r) for i, r in enumerate(shown)
                     if r['levels'][metric] == level and r['scores'][metric] is not None]
            for pos, (i, r) in enumerate(group):
                xx = bar_x + (level + .5) * zone_w + (pos-(len(group)-1)/2)*14
                color = marker_colors[i]
                c.setStrokeColor(color)
                c.setFillColor(white)
                c.setLineWidth(1.3 if i == len(shown)-1 else .7)
                path = c.beginPath()
                path.moveTo(xx-6.5, H-y-(-5))
                path.lineTo(xx, H-y-(-1))
                path.lineTo(xx+6.5, H-y-(-5))
                c.drawPath(path, stroke=1, fill=1)
                c.roundRect(xx-6.5, H-y+5, 13, 13, 4, fill=1, stroke=1)
                text(xx, y-8, f'B{r["turn"]}', 5.7, color, True)

    def numbers(y, metric, unit, headings=True):
        if headings:
            rect(table_x, y-17, table_w, 14, cyan, radius=3)
        for i, r in enumerate(shown):
            xx = table_x + (i+.5)*col_w
            if headings:
                text(xx, y-7, f'B{r["turn"]}', 7.2, navy, True)
            value = r['scores'][metric]
            label = fmt(value) if value is not None else '-'
            text(xx, y+11, label, 9, navy, True)
            text(xx, y+22, unit if value is not None else 'brak danych', 6, MUTED, True)

    def row(y, title, metric, unit='pkt', maximum=None, compact=False):
        block(title, 45 if compact else 48, y-7, 150, 10 if compact else 12, navy)
        if maximum:
            text(48, y+30, f'maks. {maximum} pkt', 8, MUTED)
        category_bar(y+9, metric)
        numbers(y+5, metric, unit)
        if any(r['scores'][metric] is not None and r['levels'][metric] is None for r in shown):
            text(bar_x, y+38, 'Brak normy: wynik bez znacznika', 6, MUTED)

    header('Twój profil alfabetyzacji ruchowej', 1)
    # Measurement dates remain visible, even when there are missing scores.
    for i, r in enumerate(shown):
        d = r.get('test')
        label = d.strftime('%d.%m.%Y') if d else 'brak daty'
        text(45+i*172, 133, f'B{r["turn"]}: {label}', 8, MUTED)
    rect(left, 148, width, 91, cyan, BORDER, 10)
    row(178, 'Ogólny wynik alfabetyzacji ruchowej', 8, maximum=100)
    text(36, 263, 'Cztery filary alfabetyzacji ruchowej', 17, navy)
    rect(left, 278, width, 102, white, BORDER, 9)
    row(306, 'Zachowania codzienne', 5, maximum=30)
    text(48, 365, 'Średnia liczba kroków/dzień', 8, navy)
    for i, r in enumerate(shown):
        v = r['scores'][3]
        text(table_x+(i+.5)*col_w, 365, fmt(v) if v is not None else '-', 8, navy, True)
    rect(left, 391, width, 209, white, BORDER, 9)
    row(419, 'Kompetencje ruchowe', 4, maximum=30)
    for y, title, metric, unit in ((476, 'CAMSA', 0, 'pkt / 28'),
                                    (520, 'Deska', 2, 's'),
                                    (564, 'Beep test', 1, 'odc.')):
        c.setStrokeColor(BORDER)
        c.setLineWidth(.5)
        c.line(45, H-y+15, 551, H-y+15)
        row(y, title, metric, unit, compact=True)
    rect(left, 611, width, 72, white, BORDER, 9)
    row(638, 'Motywacja i pewność siebie', 6, maximum=30)
    rect(left, 694, width, 72, white, BORDER, 9)
    row(721, 'Wiedza i zrozumienie', 7, maximum=10)
    for i, label in enumerate(('P: Początkujący', 'DP: Dokonujący postępów',
                                'S: Sprawny', 'W: Wyróżniający się')):
        x = 34 + (0, 116, 294, 383)[i]
        rect(x, 779, 7, 7, palette[i], radius=1)
        text(x+10, 786, label, 6.5, navy)
    text(34, 801, 'B = numer badania. Znacznik wskazuje kategorię. Ramka = kategoria ostatniego badania.', 6.7, MUTED)
    c.showPage()
    sections, advice, parent = (feedback_result if feedback_result is not None else
                                child_feedback(records, norms, keys, fmt, use_ai=use_ai))
    sections = list(sections)  # Nie modyfikuj podsumowania współdzielonego z etapem AI.
    sections += [('Czego możesz spróbować?', advice), ('Dla rodzica', parent)]
    page = 2
    header('Co mówią Twoje wyniki?', page)
    y = 142
    for title, value in sections:
        style = ParagraphStyle('Narracja', fontName='PAPL', fontSize=11, leading=15, textColor=INK,
                               alignment=TA_JUSTIFY, splitLongWords=False)
        paragraph = Paragraph(escape(keep_single_letters(value)), style)
        _, height = paragraph.wrap(511, H)
        heading_height = 22 if title else 0
        if y + heading_height + height > 788:
            c.showPage()
            page += 1
            header('Co mówią Twoje wyniki?', page)
            y = 142
        if title:
            text(42, y + 12, title, 12, TEAL)
            y += heading_height
        paragraph.drawOn(c, 42, H - y - height)
        y += height + 10
    c.showPage()
    c.save()
    return out.getvalue()

