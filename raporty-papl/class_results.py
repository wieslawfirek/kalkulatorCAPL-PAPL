"""Portrait result pages shared by class and school reports."""
from collections import Counter
from statistics import mean
from datetime import date, datetime
from xml.sax.saxutils import escape

from reportlab.platypus import Flowable, Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor, white
from reportlab.pdfbase.pdfmetrics import stringWidth

NAVY=HexColor('#091C4F')
CYAN=HexColor('#E1F5FA')
LINE=HexColor('#BED5E9')
MUTED=HexColor('#4F657B')
COLORS=tuple(map(HexColor,('#FFB3C1','#FFE16D','#B8EF88','#008B4C')))
LABELS=('Początkujący','Dokonujący postępów','Sprawny','Wyróżniający się')


def result_summary(records,turn,metric):
    rows=[r for r in records if r['turn']==turn and r['scores'][metric] is not None]
    counts=Counter(r['levels'][metric] for r in rows if r['levels'][metric] is not None)
    bins=tuple(counts[i] for i in range(4))
    return len(rows),bins,mean(r['scores'][metric] for r in rows) if rows else None


def paired_changes(records,first,last,metric):
    groups={t:{r['student']:r['levels'][metric] for r in records
               if r['turn']==t and r['scores'][metric] is not None and r['levels'][metric] is not None}
            for t in (first,last)}
    ids=groups[first].keys()&groups[last].keys()
    counts=[0,0,0]
    for student in ids:
        change=groups[last][student]-groups[first][student]
        counts[0 if change>0 else 2 if change<0 else 1]+=1
    return counts


def pct(count,total):
    return f'{100*count/total:.1f}'.rstrip('0').rstrip('.').replace('.',',')+'%' if total else '—'


class ResultsPage(Flowable):
    width=523
    height=708

    def __init__(self,records,roster,turns,metric,label,school_report=False):
        super().__init__()
        self.width=511
        self.height=708
        self.records,self.roster,self.turns=records,roster,turns
        self.metric,self.label,self.school_report=metric,label,school_report

    def draw(self):
        c=self.canv;H=self.height;W=self.width
        def rect(x,y,w,h,fill=white,border=None,radius=8):
            c.setFillColor(fill);c.setLineWidth(.6)
            if border:c.setStrokeColor(border)
            c.roundRect(x,H-y-h,w,h,radius,fill=1,stroke=bool(border))
        def text(x,y,value,size=10,color=NAVY,center=False,bold=False):
            value=str(value);c.setFillColor(color);c.setFont('PAPL',size)
            if bold:
                c.saveState();c.setStrokeColor(color);c.setLineWidth(.25)
                obj=c.beginText(x-(stringWidth(value,'PAPL',size)/2 if center else 0),H-y)
                obj.setFont('PAPL',size);obj.setTextRenderMode(2);obj.textOut(value);c.drawText(obj);c.restoreState()
            else:(c.drawCentredString if center else c.drawString)(x,H-y,value)
        def para(value,x,y,width,size=9,color=NAVY):
            p=Paragraph(escape(str(value)),ParagraphStyle('result',fontName='PAPL',fontSize=size,leading=size*1.28,textColor=color))
            _,h=p.wrap(width,700);p.drawOn(c,x,H-y-h);return h
        def line(x,y,x2,y2):
            c.setStrokeColor(LINE);c.setLineWidth(.6);c.line(x,H-y,x2,H-y2)
        room=str(self.roster[0]['classroom'])
        text(8,14,'RAPORT SZKOLNY • PAPL' if self.school_report else 'RAPORT KLASOWY • PAPL',10,bold=True)
        text(8,43,'Wyniki szkoły' if self.school_report else f'Wyniki klasy {room}',25,bold=True)
        school=str(self.roster[0]['school'])
        school_height=para(school,8,53,W-16,11)
        start=max(88,58+school_height+12)
        nturns=len(self.turns)
        mainheight=102+75*nturns+70
        rect(0,start,W,mainheight,white,LINE)
        rect(1,start+1,W-2,63,CYAN,radius=8)
        # Long metric titles wrap within a fixed, readable heading area.
        para(self.label,11,start+10,W-22,16)
        text(11,start+52,'Rozkład kategorii w kolejnych badaniach',10)
        col=start+69
        rect(5,col,W-10,23,CYAN,radius=3)
        for x,label in ((11,'Pomiar'),(198,'Kategorie PAPL'),(406,'S + W'),(477,'Średnia')):
            text(x,col+16,label,10,center=x>20,bold=True)
        barx,barw=80,286
        for index,turn in enumerate(self.turns):
            top=col+31+index*75
            if index==nturns-1:rect(5,top-2,W-10,68,CYAN)
            total,counts,average=result_summary(self.records,turn,self.metric)
            classified=sum(counts)
            text(10,top+20,f'B{turn}',17,bold=True)
            dates=sorted({r['test'].date() if isinstance(r['test'],datetime) else r['test']
                          for r in self.records if r['turn']==turn and isinstance(r.get('test'),date)})
            if len(dates)==1:text(10,top+35,dates[0].strftime('%d.%m.%Y'),6.8)
            elif dates:
                text(10,top+34,dates[0].strftime('%d.%m.%Y'),6.2)
                text(10,top+44,dates[-1].strftime('%d.%m.%Y'),6.2)
            else:text(10,top+35,'Brak daty',6.8,MUTED)
            by=top+7
            c.saveState();clip=c.beginPath();clip.roundRect(barx,H-by-24,barw,24,4);c.clipPath(clip,stroke=0)
            if not classified:
                rect(barx,by,barw,24,HexColor('#EEF1F5'),radius=0)
            offset=barx;small=[]
            for k,count in enumerate(counts):
                w=barw*count/classified if classified else 0
                if w:
                    rect(offset,by,w,24,COLORS[k],radius=0)
                    label=pct(count,classified)
                    if w>=stringWidth(label,'PAPL',9)+7:
                        text(offset+w/2,by+16,label,9,white if k==3 else NAVY,True,True)
                    else:small.append(f'{("P","DP","S","W")[k]} {label}')
                offset+=w
            c.restoreState()
            if not classified:text(barx+barw/2,by+16,'Brak przypisanych kategorii',9,MUTED,True)
            if small:text(barx,by+36,' • '.join(small),7,MUTED)
            text(406,top+24,pct(sum(counts[2:]),classified),14,center=True,bold=True)
            unit='kroków' if self.metric==3 else 's' if self.metric==2 else 'odc.' if self.metric==1 else 'pkt'
            score=f'{average:.1f}'.replace('.',',') if average is not None else '—'
            text(477,top+22,score,13,center=True,bold=True)
            if average is not None:text(477,top+36,unit,7,MUTED,True)
            text(barx,top+57,f'Wynik liczbowy: {total} • Kategoria: {classified} • Bez kategorii: {total-classified}',7,MUTED)
            if index<nturns-1:line(6,top+70,W-6,top+70)
            line(375,top+3,375,top+40);line(437,top+3,437,top+40)
        legend_y=col+31+nturns*75+7
        for i,label in enumerate(LABELS):
            x=82+(i%2)*220;y=legend_y+(i//2)*21
            rect(x,y,28,15,COLORS[i],radius=4)
            text(x+14,y+11,('P','DP','S','W')[i],9,white if i==3 else NAVY,True,True)
            text(x+35,y+11,label,8)
        text(W/2,legend_y+55,'S + W = uczniowie na poziomie co najmniej sprawnym',8,center=True)
        change_y=start+mainheight+13
        rect(0,change_y,W,130,white,LINE)
        rect(1,change_y+1,W-2,44,CYAN)
        text(11,change_y+19,'Zmiana kategorii tych samych uczniów',15,bold=True)
        if len(self.turns)>=2:
            first,last=self.turns[-2:]
            counts=paired_changes(self.records,first,last,self.metric);n=sum(counts)
            text(11,change_y+35,f'B{first} → B{last} • {n} uczniów z kategorią w obu badaniach',9)
            for i,(label,count) in enumerate(zip(('Wyższa kategoria','Ta sama kategoria','Niższa kategoria'),counts)):
                x=8+i*167
                rect(x,change_y+53,161,51,white,LINE,6)
                text(x+80.5,change_y+66,label,8.7,center=True,bold=True)
                text(x+80.5,change_y+86,pct(count,n),17,center=True,bold=True)
                text(x+80.5,change_y+99,f'{count} '+('uczeń' if count==1 else 'uczniów'),7,MUTED,True)
            text(W/2,change_y+120,'Ta sama kategoria nie wyklucza wzrostu wyniku punktowego.',8,center=True)
        else:
            text(11,change_y+35,'Dostępny jest jeden pomiar.',9)
            para('Porównanie kategorii wymaga wyników tych samych uczniów z co najmniej dwóch badań.',12,change_y+60,W-24,10,MUTED)
        guide=change_y+141
        rect(0,guide,W,54,CYAN)
        text(10,guide+16,'Jak czytać tę stronę',11,bold=True)
        para('Paski pokazują skład grupy w każdym badaniu. Zmiana kategorii dotyczy tych samych uczniów. Średnia obejmuje dostępne wyniki liczbowe; procenty kategorii — tylko wyniki z przypisaną kategorią.',10,guide+23,W-20,8)
