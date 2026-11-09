import base64
import io
import math
from pathlib import Path
from reportlab.lib.colors import HexColor, white
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

W, H = 595.28, 841.89
INK, TEAL, MUTED = map(HexColor, ('#193444', '#00685f', '#486474'))
BANDS = list(map(HexColor, ('#e4edf0', '#fbedcf', '#d3ede4', '#e3ddf4')))
BORDER, PANEL = HexColor('#cfdee6'), HexColor('#eaf5f2')
ABBR = ('P', 'DP', 'S', 'W')
LEGEND = ('P · Początkujący', 'DP · Dokonujący postępów', 'S · Sprawny', 'W · Wyróżniający się')
LABELS = ('Średnia dzienna liczba kroków', 'Samoocena aktywności fizycznej', 'Deska', 'Beep Test', 'CAMSA',
          'Kompetencje fizyczne', 'Codzienne zachowania', 'Motywacja i pewność siebie', 'Wiedza i zrozumienie', 'Mój wynik ogólny w czasie')
MONTHS = ('Sty', 'Lut', 'Mar', 'Kwi', 'Maj', 'Cze', 'Lip', 'Sie', 'Wrz', 'Paź', 'Lis', 'Gru')

def register_font():
    if 'PAPL' not in pdfmetrics.getRegisteredFontNames():
        path = Path(__file__).with_name('font.b64')
        pdfmetrics.registerFont(TTFont('PAPL', io.BytesIO(base64.b64decode(path.read_bytes()))))

def fmt(value):
    return f'{value:,.2f}'.rstrip('0').rstrip('.').replace(',', ' ').replace('.', ',')

def report(records, norms, metrics):
    register_font()
    out = io.BytesIO()
    c = Canvas(out, pagesize=(W, H))
    records = sorted(records, key=lambda r:r['turn'])
    latest = records[-1]
    keys = list(metrics)
    order = (3, 4, 2, 1, 0, 5, 6, 7, 8, 9)

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
        rect(0,0,W,7,TEAL)
        text(42,43,'CAPL-2 / RAPORT INDYWIDUALNY',9,TEAL)
        text(42,79,title,25)
        text(42,101,f'{latest["name"]}  ·  {latest["school"]}  ·  klasa {latest["classroom"]}  ·  liczba pomiarów: {len(records)}',9,MUTED)
        rect(42,119,511,1,BORDER)
        rect(42,789,511,1,BORDER)
        text(42,805,'Polskie normy PAPL · progi dobrane według wieku w dniu testu i płci',8,MUTED)
        text(535,805,f'{page}/2',8,MUTED)

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
    chart(42,135,511,258,9,'Punkty / 100',100,True)
    rect(42,405,511,55,PANEL,radius=9)
    delta=change(9,'pkt')
    text(55,425,f'Zmiana względem poprzedniego dostępnego wyniku: {delta}' if delta else 'Porównanie wyniku ogólnego wymaga dwóch dostępnych wyników.',10,TEAL)
    text(55,444,'Kolorowe pasma pokazują progi PAPL właściwe dla wieku w danym terminie.',9,MUTED)
    for k in range(4):
        chart(42+(k%2)*261,475+(k//2)*139,250,125,5+k,'Punkty / '+('10' if k==3 else '30'),10 if k==3 else 30)
    legend(766)
    c.showPage()
    header('Moja aktywność i próby ruchowe',2)
    text(42,146,'Aktywność na co dzień',15,TEAL)
    chart(42,161,250,180,0,'Kroki na dzień',None)
    chart(303,161,250,180,1,'Dni w tygodniu z co najmniej 60 min ruchu',7)
    text(42,374,'Zadania ruchowe',15,TEAL)
    for k,(unit,top) in enumerate((('Sekundy',None),('Ukończone odcinki 20 m',None),('Punkty w próbie / 28',28))):
        chart(42+k*173,388,165,185,2+k,unit,top)
    legend(597)
    rect(42,618,511,112,PANEL,radius=9)
    text(55,641,'Co się zmieniło?',12,TEAL)
    beep,steps=change(3,'odc.'),change(0,'kroków')
    lines=[f'Beep Test: {beep}' if beep else '',f'Średnia dzienna liczba kroków: {steps}' if steps else '']
    text(55,661,' · '.join(v for v in lines if v) or 'Do porównania tych prób potrzebne są dwa dostępne wyniki.',9)
    text(55,687,'Co możesz wypróbować?',12,TEAL)
    text(55,707,'Wybierzcie razem dwa popołudnia na spacer albo zabawę na dworze.',9)
    c.showPage()
    c.save()
    return out.getvalue()
