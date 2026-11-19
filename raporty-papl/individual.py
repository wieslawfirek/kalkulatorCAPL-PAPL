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

    def text(x, y, value, size=10, color=INK, centered=False, bold=False):
        c.setFont('PAPL', size)
        c.setFillColor(color)
        if bold:
            c.saveState()
            value = str(value)
            offset = pdfmetrics.stringWidth(value, 'PAPL', size)/2 if centered else 0
            obj = c.beginText(x-offset, H-y)
            obj.setFont('PAPL', size)
            obj.setTextRenderMode(2)
            c.setStrokeColor(color)
            c.setLineWidth(.28)
            obj.textOut(value)
            c.drawText(obj)
            c.restoreState()
        else:
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
    palette = tuple(map(HexColor, ('#FFB3C1', '#FFE16D', '#B8EF88', '#008B4C')))
    navy = HexColor('#091C4F')
    cyan = HexColor('#DDF5FA')
    marker_colors = (HexColor('#758295'), HexColor('#1776BB'), navy)
    left, width = 24, 547
    bar_x, bar_w, table_x, table_w = 215, 184, 416, 143
    col_w = table_w / len(shown)

    def category_bar(y, metric):
        zone_w = bar_w / 4
        c.saveState()
        clip = c.beginPath()
        clip.roundRect(bar_x, H-y-18, bar_w, 18, 9)
        c.clipPath(clip, stroke=0)
        for level, color in enumerate(palette):
            rect(bar_x + level * zone_w, y, zone_w, 18, color)
        c.restoreState()
        for level in range(4):
            text(bar_x + (level+.5)*zone_w, y+13, ABBR[level], 10,
                 white if level == 3 else navy, True, True)
        current = shown[-1]['levels'][metric]
        if current is not None and shown[-1]['scores'][metric] is not None:
            c.setStrokeColor(navy)
            c.setLineWidth(1.8)
            c.roundRect(bar_x+current*zone_w-1, H-y-19, zone_w+2, 20,
                        5, fill=0, stroke=1)
        for level in range(4):
            group = [(i,r) for i,r in enumerate(shown)
                     if r['levels'][metric] == level and r['scores'][metric] is not None]
            for pos,(i,r) in enumerate(group):
                xx = bar_x+(level+.5)*zone_w+(pos-(len(group)-1)/2)*15
                color = marker_colors[i]
                c.setStrokeColor(color)
                c.setFillColor(white)
                c.setLineWidth(1.4 if i == len(shown)-1 else .85)
                path = c.beginPath()
                path.moveTo(xx-7, H-y+6)
                path.lineTo(xx, H-y+1)
                path.lineTo(xx+7, H-y+6)
                path.lineTo(xx+7, H-y+15)
                path.curveTo(xx+7,H-y+20,xx-7,H-y+20,xx-7,H-y+15)
                path.close()
                c.drawPath(path,stroke=1,fill=1)
                text(xx,y-8,f'B{r["turn"]}',6.1,color,True,True)

    def numbers(y, metric, unit, headings=True):
        c.setLineWidth(.4)
        rect(table_x,y-17,table_w,44,white,HexColor('#C7D6E9'),5)
        if headings:
            rect(table_x, y-17, table_w, 14, cyan, radius=4)
        for i, r in enumerate(shown):
            xx = table_x + (i+.5)*col_w
            if headings:
                text(xx, y-7, f'B{r["turn"]}', 8, navy, True, True)
            value = r['scores'][metric]
            label = fmt(value) if value is not None else '-'
            text(xx, y+11, label, 10, navy, True, True)
            text(xx, y+22, unit if value is not None else 'brak danych', 6, MUTED, True)

    def icon(kind, x, y, color):
        rect(x,y,34,34,color,radius=9)
        c.saveState()
        c.setStrokeColor(white)
        c.setFillColor(white)
        c.setLineWidth(1.7)
        c.setLineCap(1)
        def line(a,b,d,e):
            c.line(x+a,H-y-b,x+d,H-y-e)
        def circle(a,b,r,fill=0):
            c.circle(x+a,H-y-b,r,stroke=1,fill=fill)
        if kind == 'walk':
            circle(21,7,2.3,1)
            for pts in ((18,12,13,19),(18,12,23,18),(23,18,28,18),
                        (17,14,10,13),(10,13,6,18),(14,19,22,22),
                        (22,22,25,29),(14,19,10,26),(10,26,5,28)):
                line(*pts)
        elif kind == 'strength':
            line(9,17,25,17)
            for a in (7,25):
                c.roundRect(x+a-2,H-y-24,4,14,1,stroke=1,fill=0)
            line(3,14,3,20);line(31,14,31,20)
        elif kind == 'smile':
            circle(17,17,11)
            circle(13,15,.7,1);circle(21,15,.7,1)
            path=c.beginPath();path.moveTo(x+12,H-y-21)
            path.curveTo(x+15,H-y-25,x+19,H-y-25,x+23,H-y-20)
            c.drawPath(path)
        else:
            for a,b,r in ((12,10,5),(21,10,5),(9,18,5),(24,18,5),(13,25,5),(21,25,5)):
                circle(a,b,r)
            line(17,6,17,29)
        c.restoreState()

    def card(y,h,fill=white):
        rect(left+1,y+2,width,h,HexColor('#EAF0F7'),radius=12)
        c.setLineWidth(.7)
        rect(left,y,width,h,fill,HexColor('#C7D6E9'),12)

    def row(y, title, metric, unit='pkt', maximum=None, compact=False, symbol=None):
        if symbol:
            kind,color=symbol
            icon(kind,35,y-12,HexColor(color))
        x=41 if compact else (79 if symbol else 40)
        title_width=128 if symbol else 163
        labels = title.split('|')
        for i,label in enumerate(labels):
            text(x,y+4+i*13,label,10.5 if compact else 11.5,navy,bold=True)
        if maximum:
            text(x,y+9+len(labels)*13,f'(maks. {maximum} pkt)',8.5,navy)
        category_bar(y+9, metric)
        numbers(y+5, metric, unit)
        c.setStrokeColor(HexColor('#86BED0'))
        c.setLineWidth(.6)
        c.line(408,H-y+12,408,H-y-30)
        if any(r['scores'][metric] is not None and r['levels'][metric] is None for r in shown):
            text(bar_x,y+38,'Brak normy: wynik bez znacznika',6,MUTED)

    report_frame(c,W,H,1)
    rect(0,49,W,H-84,white)
    text(W/2,78,'Twój profil alfabetyzacji ruchowej',21,navy,True,True)
    rect(111,89,373,21,cyan,radius=10)
    text(W/2,104,f'PAPL • {latest["name"]} • klasa {latest["classroom"]}',10,navy,True,True)
    block(latest['school'],40,115,515,8,MUTED)
    # Measurement dates remain visible, even when there are missing scores.
    for i, r in enumerate(shown):
        d = r.get('test')
        label = d.strftime('%d.%m.%Y') if d else 'brak daty'
        text(45+i*172, 133, f'B{r["turn"]}: {label}', 8, MUTED)
    card(148,91,cyan)
    row(178, 'Ogólny wynik|alfabetyzacji|ruchowej', 8, maximum=100)
    text(W/2,263,'Cztery filary alfabetyzacji ruchowej',18,navy,True,True)
    card(278,102)
    row(306,'Zachowania|codzienne',5,maximum=30,symbol=('walk','#22BDDE'))
    rect(38,349,521,23,HexColor('#F0F8FD'),radius=6)
    text(48,364,'Kroki/dzień',9,navy,bold=True)
    for i, r in enumerate(shown):
        v = r['scores'][3]
        text(table_x+(i+.5)*col_w, 365, fmt(v) if v is not None else '-', 8, navy, True)
    card(391,209)
    row(419,'Kompetencje|ruchowe',4,maximum=30,symbol=('strength','#69C41A'))
    for y, title, metric, unit in ((476, 'CAMSA', 0, 'pkt / 28'),
                                    (520, 'Deska', 2, 's'),
                                    (564, 'Beep test', 1, 'odc.')):
        c.setStrokeColor(BORDER)
        c.setLineWidth(.5)
        c.line(45, H-y+15, 551, H-y+15)
        row(y, title, metric, unit, compact=True)
    card(611,72)
    row(634,'Motywacja|i pewność siebie',6,maximum=30,symbol=('smile','#F5B900'))
    card(694,72)
    row(717,'Wiedza|i zrozumienie',7,maximum=10,symbol=('brain','#A580D9'))
    rect(24,776,547,20,cyan,radius=8)
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

