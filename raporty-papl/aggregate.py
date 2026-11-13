import io
from collections import Counter
from statistics import mean
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from individual import register_font

TURNS = {1: 'Pretest', 2: 'Posttest', 3: 'Pomiar po roku'}
LEVELS = ('Początkujący', 'Dokonujący postępów', 'Sprawny', 'Wyróżniający się')
METRICS = (
    (8, 'Ogólny wynik alfabetyzacji ruchowej'),
    (4, 'Kompetencje fizyczne'),
    (5, 'Zachowania codzienne'),
    (6, 'Motywacja i pewność siebie'),
    (7, 'Wiedza i zrozumienie'),
)
BANDS = tuple(map(HexColor, ('#F2BAAA', '#F4D794', '#A9D7AD', '#68B8A2')))
GREEN = HexColor('#174A3A')
INK = HexColor('#173029')
MUTED = HexColor('#52655B')
RULE = HexColor('#D7E2DA')
PAPER = HexColor('#F4F7F4')
WIDTH = 511

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

def paragraph(value, size=10, color=INK):
    style = ParagraphStyle('PAPL', fontName='PAPL', fontSize=size,
                           leading=size * 1.3, textColor=color, splitLongWords=True)
    return Paragraph(escape(value), style)


def grid(rows, widths, *, card=False, padding=0):
    table = Table(rows, colWidths=widths, hAlign='LEFT')
    commands = [
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), padding),
        ('RIGHTPADDING', (0, 0), (-1, -1), padding),
        ('TOPPADDING', (0, 0), (-1, -1), padding),
        ('BOTTOMPADDING', (0, 0), (-1, -1), padding),
    ]
    if card:
        commands += [('BACKGROUND', (0, 0), (-1, -1), white),
                     ('BOX', (0, 0), (-1, -1), 0.6, RULE)]
    table.setStyle(TableStyle(commands))
    return table


def card(items, width):
    return grid([[items]], [width], card=True, padding=11)


def legend():
    draw = Drawing(WIDTH, 22)
    x = 0
    for level, color in zip(LEVELS, BANDS):
        draw.add(Rect(x, 6, 10, 10, fillColor=color, strokeColor=None))
        draw.add(String(x + 15, 7, level, fontName='PAPL', fontSize=9, fillColor=INK))
        x += 29 + stringWidth(level, 'PAPL', 9)
    return draw


def distribution_row(label, available, counts, width):
    n = sum(counts)
    narrow = width < 250
    shift = 11 if narrow else 0
    draw = Drawing(width, 52 + shift)
    draw.add(Rect(0, 17 + shift, width, 17, fillColor=PAPER, strokeColor=None))
    if n:
        x = 0
        for count, color in zip(counts, BANDS):
            segment = width * count / n
            if count:
                draw.add(Rect(x, 17 + shift, segment, 17, fillColor=color, strokeColor=None))
                value = percent(count, n)
                if segment >= stringWidth(value, 'PAPL', 8) + 6:
                    draw.add(String(x + segment / 2, 23 + shift, value, textAnchor='middle',
                                    fontName='PAPL', fontSize=8, fillColor=INK))
            x += segment
        details = '  /  '.join(percent(count, n) for count in counts)
        benchmark = f'Co najmniej sprawny {percent(sum(counts[2:]), n)}'
        if narrow:
            draw.add(String(0, 5, benchmark, fontName='PAPL', fontSize=8, fillColor=MUTED))
        else:
            details += '   ·   ' + benchmark
    else:
        details = 'Brak kategorii PAPL w tym pomiarze'
    draw.add(String(0, 5 + shift, details, fontName='PAPL', fontSize=8, fillColor=MUTED))
    sample = f'n = {n}' + (f' · bez kategorii {available - n}' if available > n else '')
    draw.add(String(width, 39 + shift, sample, textAnchor='end', fontName='PAPL', fontSize=8, fillColor=MUTED))
    label_width = width - stringWidth(sample, 'PAPL', 8) - 8
    short_label = label
    while short_label and stringWidth(short_label + ('…' if short_label != label else ''), 'PAPL', 9) > label_width:
        short_label = short_label[:-1]
    if short_label != label:
        short_label += '…'
    draw.add(String(0, 39 + shift, short_label, fontName='PAPL', fontSize=9, fillColor=INK))
    return draw


def charts(records, turns, metric, width):
    return [distribution_row(TURNS[turn], *distribution(records, turn, metric), width)
            for turn in turns]


def changes(records, turns):
    items = [paragraph('Zmiana poziomu u tych samych uczniów', 13, GREEN), Spacer(1, 5)]
    comparable = [turn for turn in turns if sum(distribution(records, turn, 8)[1])]
    if len(comparable) < 2:
        items.append(paragraph('Porównanie wymaga kategorii w co najmniej dwóch pomiarach.', 9, MUTED))
    for first, second in zip(comparable, comparable[1:]):
        counts = transitions(records, first, second)
        n = sum(counts.values())
        up = sum(value for (start, end), value in counts.items() if end > start)
        down = sum(value for (start, end), value in counts.items() if end < start)
        items.append(paragraph(f'{TURNS[first]} → {TURNS[second]} · n = {n}', 10))
        if n:
            items.append(paragraph(f'Awans {up} · Bez zmiany {n - up - down} · Spadek {down}', 9, MUTED))
        else:
            items.append(paragraph('Brak uczniów z kategorią w obu pomiarach.', 9, MUTED))
        items.append(Spacer(1, 6))
    return items


def aggregate_pdf(records, roster, title, by_class=False):
    register_font()
    out = io.BytesIO()
    reference = roster[0]['turn']
    turns = sorted({row['turn'] for row in records if any(v is not None for v in row['scores'])})
    scope = 'Raport szkolny' if by_class else 'Raport klasowy'

    def heading(label):
        return [paragraph(scope.upper(), 9, GREEN), Spacer(1, 5), paragraph(title, 21),
                paragraph(label, 14, GREEN), Spacer(1, 9)]

    items = heading('Wynik ogólny alfabetyzacji ruchowej')
    items += [paragraph(f'Skład grupy według pomiaru „{TURNS[reference]}” · {len(roster)} uczniów z wynikiem', 9, MUTED),
              Spacer(1, 6), legend()]
    distribution_card = card([paragraph('Rozkład poziomów', 13, GREEN), Spacer(1, 5),
                              *charts(records, turns, 8, 316)], 338)
    score_items = [paragraph('Średni wynik', 13, GREEN), Spacer(1, 5)]
    for turn in turns:
        values = [row['scores'][8] for row in records if row['turn'] == turn and row['scores'][8] is not None]
        result = f'{mean(values):.1f}'.replace('.', ',') + ' pkt' if values else 'Brak wyniku'
        score_items += [paragraph(f'{TURNS[turn]} · n = {len(values)}', 8, MUTED),
                        paragraph(result, 13), Spacer(1, 7)]
    items += [grid([[distribution_card, '', card(score_items, 161)]], [338, 12, 161]), Spacer(1, 10),
              card(changes(records, turns), WIDTH), Spacer(1, 7),
              paragraph('Słupki obejmują uczniów z kategorią PAPL. Średnie uwzględniają wszystkie dostępne wyniki ogólne. Kategorie zależą od wieku w dniu testu i płci.', 8, MUTED)]

    comparison = []
    if by_class:
        classes = sorted({row['classroom'] for row in roster})
        by_student = {row['student']: row['classroom'] for row in roster}
        latest = {room: [] for room in classes}
        for row in records:
            if row['turn'] == turns[-1]:
                latest[by_student[row['student']]].append(row)
        for room in classes:
            comparison.append(distribution_row(f'Klasa {room}', *distribution(latest[room], turns[-1], 8), WIDTH - 22))
        if len(comparison) <= 4 and len(title) <= 75:
            items += [Spacer(1, 10), card([paragraph(f'Porównanie klas · {TURNS[turns[-1]]}', 13, GREEN),
                                         Spacer(1, 5), *comparison], WIDTH)]
            comparison = []

    items += [PageBreak(), *heading('Cztery obszary alfabetyzacji ruchowej'), legend()]
    panels = [card([paragraph(label, 12, GREEN), Spacer(1, 8), *charts(records, turns, metric, 227)], 249)
              for metric, label in METRICS[1:]]
    items += [grid([[panels[0], '', panels[1]]], [249, 13, 249]), Spacer(1, 13),
              grid([[panels[2], '', panels[3]]], [249, 13, 249]), Spacer(1, 10),
              paragraph('Kolejność wartości pod słupkami odpowiada legendzie. n oznacza liczbę uczniów z kategorią PAPL w danym pomiarze i obszarze.', 8, MUTED)]

    if comparison:
        items += [PageBreak(), *heading(f'Porównanie klas · {TURNS[turns[-1]]}'), legend()]
        items += [KeepTogether([card([row], WIDTH), Spacer(1, 3)]) for row in comparison]

    def decorate(canvas, doc):
        width, height = A4
        canvas.setFillColor(PAPER)
        canvas.rect(0, 0, width, height, fill=1, stroke=0)
        canvas.setFillColor(GREEN)
        canvas.rect(0, height - 47, width, 47, fill=1, stroke=0)
        canvas.setFont('PAPL', 13)
        canvas.setFillColor(white)
        canvas.drawString(42, height - 29, 'RAPORTY · CAPL')
        canvas.setFont('PAPL', 9)
        canvas.drawRightString(width - 42, height - 28, 'Polskie normy PAPL')
        canvas.setFillColor(MUTED)
        canvas.drawString(42, 24, 'Ocena alfabetyzacji ruchowej')
        canvas.drawRightString(width - 42, 24, str(doc.page))

    SimpleDocTemplate(out, pagesize=A4, leftMargin=36, rightMargin=36,
                      topMargin=56, bottomMargin=38).build(
        items, onFirstPage=decorate, onLaterPages=decorate)
    return out.getvalue()
