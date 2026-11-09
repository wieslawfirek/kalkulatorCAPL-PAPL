import io
from collections import Counter

from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib.colors import white
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from xml.sax.saxutils import escape

from individual import BANDS, BORDER, INK, MUTED, TEAL, register_font

TURNS = {1:'Pretest',2:'Posttest',3:'Pomiar po roku'}
LEVELS = ('Początkujący','Dokonujący postępów','Sprawny','Wyróżniający się')
SHORT = ('P','DP','S','W')
METRICS = (
    (8,'Ogólny wynik alfabetyzacji ruchowej'),
    (4,'Kompetencje fizyczne'),
    (5,'Zachowania codzienne'),
    (6,'Motywacja i pewność siebie'),
    (7,'Wiedza i zrozumienie'),
)

def reference_rosters(records):
    last = {}
    has_history = set()
    for row in records:
        if any(value is not None for value in row['scores']):
            school = row['school']
            last[school] = max(last.get(school, 0), row['turn'])
            has_history.add(row['student'])
    return [row for row in records if row['turn'] == last.get(row['school'])
            and row['student'] in has_history]

def group_history(records, roster):
    ids = {row['student'] for row in roster}
    return [row for row in records if row['student'] in ids]

def distribution(records, turn, metric):
    available = [row for row in records if row['turn']==turn and row['scores'][metric] is not None]
    counts = Counter(row['levels'][metric] for row in available if row['levels'][metric] is not None)
    return len(available), tuple(counts[i] for i in range(4))

def transitions(records, first, second):
    by_turn = {
        turn:{r['student']:r['levels'][8] for r in records if r['turn']==turn and r['levels'][8] is not None}
        for turn in (first, second)
    }
    start, end = by_turn[first], by_turn[second]
    return Counter((start[key],end[key]) for key in start.keys() & end.keys())

def percent(value, total):
    return f'{100*value/total:.1f}'.replace('.', ',')+'%' if total else '—'

def chart(title, records, turns, metric):
    width = 495
    height = 42+27*len(turns)
    draw = Drawing(width,height)
    def label(x,y,text,size=8,color=INK,anchor='start'):
        draw.add(String(x,y,text,fontName='PAPL',fontSize=size,fillColor=color,textAnchor=anchor))
    label(0,height-13,title,11,TEAL)
    left, span = 115, 368
    for pct in range(0,101,25):
        x=left+span*pct/100
        label(x,height-28,f'{pct}%',7,MUTED,'middle')
        draw.add(Line(x,3,x,height-32,strokeColor=BORDER,strokeWidth=.4))
    for i,turn in enumerate(turns):
        y=height-49-27*i
        label(0,y+2,TURNS[turn],8)
        available, counts=distribution(records,turn,metric)
        n=sum(counts)
        if n:
            offset=left
            for color,count in zip(BANDS,counts):
                w=span*count/n
                if count:
                    draw.add(Rect(offset,y,w,12,fillColor=color,strokeColor=None))
                    if w>=33:
                        label(offset+w/2,y+3,percent(count,n),7,INK,'middle')
                    offset+=w
        else:
            label(left+4,y+3,'Brak kategorii PAPL',8,MUTED)
        details=' · '.join(f'{key} {percent(count,n)}' for key,count in zip(SHORT,counts)) if n else ''
        counts_text=f'Z kategorią: {n} · Z wynikiem bez kategorii: {available-n}'
        label(0,y-10,counts_text+(f'   |   {details}' if details else ''),7,MUTED)
    return draw

def aggregate_pdf(records, roster, title, by_class=False):
    register_font()
    styles=getSampleStyleSheet()
    for style in ('Title','Heading2','Normal'):
        styles[style].fontName='PAPL'
        styles[style].textColor=INK
    styles['Normal'].leading=13
    items=[]
    out=io.BytesIO()
    reference=roster[0]['turn']
    all_turns=sorted({r['turn'] for r in records if any(v is not None for v in r['scores'])})
    def paragraph(value,style='Normal'):
        return Paragraph(escape(value),styles[style])
    def distributions_page(heading, history, size):
        items.extend([paragraph(heading,'Title'),
                      paragraph(f'Skład według pomiaru: {TURNS[reference]} · {size} uczniów z wynikiem w co najmniej jednej turze'),
                      paragraph('Każdy słupek pokazuje odsetki wśród uczniów z kategorią PAPL w danej turze.'),
                      Spacer(1,6),
                      paragraph(' · '.join(f'{s} – {l}' for s,l in zip(SHORT,LEVELS)))])
        for metric,label in METRICS:
            items.append(chart(label,history,all_turns,metric))
    distributions_page(title,records,len(roster))
    overall_turns=[turn for turn in all_turns if sum(distribution(records,turn,8)[1])]
    if len(all_turns)>1:
        items.extend([PageBreak(),paragraph('Przejścia między kategoriami PAPL','Title'),
                      paragraph(title),paragraph('Wynik ogólny. Porównanie obejmuje uczniów z kategorią w obu turach, połączonych według identyfikatora.')])
        if len(overall_turns)<2:
            items.append(paragraph('Brak dwóch tur z dostępnymi kategoriami wyniku ogólnego.'))
        for first,second in zip(overall_turns,overall_turns[1:]):
            counts=transitions(records,first,second)
            n=sum(counts.values())
            items.append(paragraph(f'{TURNS[first]} → {TURNS[second]}','Heading2'))
            if not n:
                items.append(paragraph('Brak uczniów z kategorią w obu turach.'))
                continue
            up=sum(value for (a,b),value in counts.items() if b>a)
            down=sum(value for (a,b),value in counts.items() if b<a)
            items.append(paragraph(f'Pary: {n} · Wyżej: {percent(up,n)} · Bez zmiany: {percent(n-up-down,n)} · Niżej: {percent(down,n)}'))
            items.append(Spacer(1,6))
            rows=[['Z kategorii / do kategorii',*SHORT],*[[SHORT[a],*[counts[a,b] for b in range(4)]] for a in range(4)]]
            table=Table(rows,colWidths=[167,82,82,82,82],hAlign='LEFT')
            styles_table=[('FONTNAME',(0,0),(-1,-1),'PAPL'),('FONTSIZE',(0,0),(-1,-1),8),
                          ('BACKGROUND',(0,0),(-1,0),BORDER),('BACKGROUND',(0,1),(0,-1),BORDER),
                          ('ALIGN',(1,0),(-1,-1),'CENTER'),('GRID',(0,0),(-1,-1),.5,white),
                          ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]
            for a in range(4):
                for b in range(4):
                    if counts[a,b]:
                        styles_table.append(('BACKGROUND',(b+1,a+1),(b+1,a+1),BANDS[2 if b>a else 1 if b<a else 0]))
            table.setStyle(TableStyle(styles_table))
            items.append(table)
        items.append(Spacer(1,10))
        items.append(paragraph('Kategorie w każdej turze ustalono według wieku w dniu testu i płci. Przejście między kategoriami może odzwierciedlać zmianę wyniku lub progu wieku.'))
    if by_class:
        for room in sorted({r['classroom'] for r in roster}):
            members=[r for r in roster if r['classroom']==room]
            items.append(PageBreak())
            distributions_page(f'{title} · klasa {room}',group_history(records,members),len(members))
    if len(all_turns)==1 and not by_class:
        items.append(paragraph('Dostępny jest jeden pomiar. Porównanie zmian wymaga wyników z kolejnej tury.'))
    def page(canvas,doc):
        canvas.setFillColor(TEAL)
        canvas.rect(0,A4[1]-7,A4[0],7,fill=1,stroke=0)
        canvas.setFont('PAPL',8)
        canvas.drawString(44,26,'CAPL-2 · polskie normy PAPL')
        canvas.drawRightString(551,26,str(doc.page))
    SimpleDocTemplate(out,pagesize=A4,leftMargin=44,rightMargin=44,topMargin=36,bottomMargin=39).build(
        items,onFirstPage=page,onLaterPages=page)
    return out.getvalue()
