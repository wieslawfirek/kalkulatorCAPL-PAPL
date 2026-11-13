import base64
import io
import math
from pathlib import Path
from reportlab.lib.colors import white
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from xml.sax.saxutils import escape

from branding import BANDS, GREEN as TEAL, INK, MUTED, PAPER as PANEL, RULE as BORDER, report_frame
from feedback import child_feedback
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

W, H = 595.28, 841.89
ABBR = ('P', 'DP', 'S', 'W')
LEGEND = ('P · Początkujący', 'DP · Dokonujący postępów', 'S · Sprawny', 'W · Wyróżniający się')
LABELS = ('Średnia dzienna liczba kroków', 'Deska', 'Beep Test', 'CAMSA',
          'Kompetencje fizyczne', 'Codzienne zachowania', 'Motywacja i pewność siebie', 'Wiedza i zrozumienie', 'Mój wynik ogólny w czasie')
MONTHS = ('Sty', 'Lut', 'Mar', 'Kwi', 'Maj', 'Cze', 'Lip', 'Sie', 'Wrz', 'Paź', 'Lis', 'Gru')

def register_font():
    if 'PAPL' not in pdfmetrics.getRegisteredFontNames():
        path = Path(__file__).with_name('font.b64')
        pdfmetrics.registerFont(TTFont('PAPL', io.BytesIO(base64.b64decode(path.read_bytes()))))

def fmt(value):
    return f'{value:,.2f}'.rstrip('0').rstrip('.').replace(',', ' ').replace('.', ',')

def report(records, norms, metrics, use_ai=True):
    register_font()
    out = io.BytesIO()
    c = Canvas(out, pagesize=(W, H))
    records = sorted(records, key=lambda r:r['turn'])
    latest = records[-1]
    keys = list(metrics)
    order = (3, 2, 1, 0, 4, 5, 6, 7, 8)

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

    def chart(x, y, w, h, idx, unit, maximum, show_age=False):
        j = order[idx]
        values = [r['scores'][j] for r in records]
        thresholds = [norms.get((r['sex'],r['age'],keys[j])) for r in records]
        top = maximum or max([1]+[v for v in values if v is not None]+[n[3] for n in thresholds if n])
        if not maximum:
            scale=10**math.floor(math.log10(top))
            top=math.ceil(top/scale*2)/2*scale
        rect(x,y,w,h,white,BORDER,10)
        text(x+13,y+19,LABELS[idx],11 if w<280 else 14)
        text(x+13,y+34,unit,8,MUTED)
        left, plotw = x+34,w-49
        start,end = y+45,y+h-(45 if show_age else 29)
        step=plotw/len(records)
        py=lambda v:end-(end-start)*max(0,min(top,v))/top
        for i,n in enumerate(thresholds):
            if n:
                bounds=(0,*n[1:],top)
                for a,b,color in zip(bounds,bounds[1:],BANDS):
                    rect(left+i*step+2,py(b),step-4,max(0,py(a)-py(b)),color)
        c.setStrokeColor(BORDER); c.setLineWidth(.45)
        for v in (0,top/2,top):
            yy=py(v)
            c.line(left,H-yy,left+plotw,H-yy)
            text(left-17,yy+2,fmt(v),6.5,MUTED,True)
        previous=None
        for i,(r,v) in enumerate(zip(records,values)):
            xx=left+(i+.5)*step
            d=r['test']
            label=f'{MONTHS[d.month-1]} {d.year}' if d else f'Pomiar {r["turn"]}'
            text(xx,end+15,label,7,MUTED,True)
            if show_age:
                text(xx,end+29,f'{r["age"]} lat' if r['age'] is not None else 'Brak wieku',7,MUTED,True)
            if v is None:
                previous=None
                text(xx,end-8,'Brak',7,MUTED,True)
                continue
            yy=py(v)
            c.setStrokeColor(TEAL);c.setLineWidth(1.5)
            if previous:
                c.line(previous[0],H-previous[1],xx,H-yy)
            previous=xx,yy
            c.setFillColor(TEAL);c.circle(xx,H-yy,3.3,fill=1,stroke=0)
            level=r['levels'][j]
            label=fmt(v)+(f' · {ABBR[level]}' if level is not None else '')
            sw=pdfmetrics.stringWidth(label,'PAPL',7.5)+8
            ly=yy-14 if yy>start+13 else yy+6
            rect(xx-sw/2,ly-2,sw,11,white,radius=3)
            text(xx,ly+6,label,7.5,INK,True)

    def header(title,page):
        report_frame(c, W, H, page)
        text(42,67,'RAPORT INDYWIDUALNY',9,TEAL)
        text(42,94,title,23)
        metadata = f'{latest["name"]} · {latest["school"]} · klasa {latest["classroom"]} · pomiary {len(records)}'
        block(metadata, 42, 103, 511, 9, MUTED)

    def block(value, x, y, width, size, color=INK):
        style = ParagraphStyle('PAPL', fontName='PAPL', fontSize=size, leading=size*1.28, textColor=color)
        paragraph = Paragraph(escape(value), style)
        _, height = paragraph.wrap(width, H)
        paragraph.drawOn(c, x, H-y-height)
        return height

    def legend(y):
        for i,label in enumerate(LEGEND):
            x=42+i*128
            rect(x,y-7,9,9,BANDS[i],radius=2)
            text(x+13,y,label,7.5,MUTED)

    def change(idx, unit):
        j=order[idx]
        available=[r['scores'][j] for r in records if r['scores'][j] is not None]
        if len(available)<2:
            return None
        delta=available[-1]-available[-2]
        return ('+' if delta>0 else '')+fmt(delta)+' '+unit

    header('Mój profil alfabetyzacji ruchowej',1)
    chart(42,135,511,258,8,'Punkty / 100',100,True)
    rect(42,405,511,55,PANEL,radius=9)
    delta=change(8,'pkt')
    text(55,425,f'Zmiana względem poprzedniego dostępnego wyniku: {delta}' if delta else 'Porównanie wyniku ogólnego wymaga dwóch dostępnych wyników.',10,TEAL)
    text(55,444,'Kolorowe pasma pokazują progi PAPL właściwe dla wieku w danym terminie.',9,MUTED)
    for k in range(4):
        chart(42+(k%2)*261,475+(k//2)*139,250,125,4+k,'Punkty / '+('10' if k==3 else '30'),10 if k==3 else 30)
    legend(766)
    c.showPage()
    header('Moja aktywność i próby ruchowe',2)
    measures = (('Kroki na dzień', None), ('Sekundy', None),
                ('Ukończone odcinki 20 m', None), ('Punkty w próbie / 28', 28))
    for k, (unit, top) in enumerate(measures):
        chart(42+(k%2)*261, 135+(k//2)*194, 250, 177, k, unit, top)
    legend(524)
    description, advice = child_feedback(records, norms, keys, fmt, use_ai=use_ai)
    rect(42,538,511,253,white,BORDER,10)
    text(55,560,'Co mówią Twoje wyniki?',13,TEAL)
    end = 570 + block(description, 55, 570, 485, 11)
    text(55,end+18,'Czego możesz spróbować?',12,TEAL)
    end += 25 + block(advice, 55, end+25, 485, 11)
    text(55,end+18,'Dla rodzica',12,TEAL)
    block('Zapytaj dziecko, co z raportu zwróciło jego uwagę. Wybierzcie razem jedną aktywność, na którą ma ochotę, i umówcie się, kiedy jej spróbujecie.', 55, end+25, 485, 11)
    c.showPage()
    c.save()
    return out.getvalue()
