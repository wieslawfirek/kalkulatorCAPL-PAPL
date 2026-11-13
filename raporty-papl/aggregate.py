import io
from collections import Counter
from statistics import mean
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib.colors import white
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from individual import register_font
from branding import BANDS, GREEN, INK, MUTED, RULE, PAPER, report_frame
from feedback import TEACHER, model_choice

TURNS = {1: 'Pretest', 2: 'Posttest', 3: 'Pomiar po roku'}
LEVELS = ('Początkujący', 'Dokonujący postępów', 'Sprawny', 'Wyróżniający się')
METRICS = (
    (8, 'Ogólny wynik alfabetyzacji ruchowej'),
    (4, 'Kompetencje fizyczne'),
    (5, 'Zachowania codzienne'),
    (6, 'Motywacja i pewność siebie'),
    (7, 'Wiedza i zrozumienie'),
)
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


def aggregate_pdf(records, roster, title, by_class=False, use_ai=True):
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

    items += [PageBreak(), *heading('Co wyniki podpowiadają do dalszej pracy?'),
              *teacher_feedback(records, roster, turns, by_class, use_ai)]

    def decorate(canvas, doc):
        report_frame(canvas, *A4, doc.page)

    SimpleDocTemplate(out, pagesize=A4, leftMargin=36, rightMargin=36,
                      topMargin=56, bottomMargin=38).build(
        items, onFirstPage=decorate, onLaterPages=decorate)
    return out.getvalue()


def teacher_feedback(records, roster, turns, by_class, use_ai):
    latest = turns[-1]
    _, overall = distribution(records, latest, 8)
    n = sum(overall)
    summary = (f'{TURNS[latest]}. Poziom co najmniej „Sprawny” w wyniku ogólnym osiągnęło '
               f'{sum(overall[2:])} z {n} uczniów z kategorią ({percent(sum(overall[2:]), n)}).'
               if n else f'{TURNS[latest]}. Brak kategorii PAPL dla wyniku ogólnego.')
    items = [paragraph(summary, 11), Spacer(1, 7)]
    candidates = {}
    strengths = []
    for metric, label in METRICS[1:]:
        _, counts = distribution(records, latest, metric)
        size = sum(counts)
        if size:
            low = sum(counts[:2])
            strengths.append((sum(counts[2:])/size, label, sum(counts[2:]), size))
            if low * 2 >= size:
                candidates[f'K{metric-3}'] = (low/size, f'{label}. Dwie niższe kategorie obejmują {low} z {size} uczniów ({percent(low, size)}).')
    if strengths:
        share, label, high, size = max(strengths)
        if share >= .5:
            items += [paragraph(f'Najwyższy odsetek wyników co najmniej „Sprawny” odnotowano w obszarze „{label}” ({high} z {size}, {percent(high, size)}).', 10), Spacer(1, 6)]
    if len(turns) > 1:
        first = turns[-2]
        _, previous = distribution(records, first, 8)
        if n and sum(previous):
            difference = 100 * (sum(overall[2:])/n - sum(previous[2:])/sum(previous))
            difference_text = f'{difference:+.1f}'.replace('.', ',')
            items += [paragraph(f'{TURNS[first]} → {TURNS[latest]}. Zmiana udziału na poziomie co najmniej „Sprawny” wynosi {difference_text} pkt proc. (n = {sum(previous)} i {n}).', 10), Spacer(1, 6)]
        counts = transitions(records, first, latest)
        up = sum(v for (a,b),v in counts.items() if b>a)
        down = sum(v for (a,b),v in counts.items() if b<a)
        paired = sum(counts.values())
        if paired:
            items += [paragraph(f'Wśród {paired} uczniów z kategorią w obu pomiarach {up} przeszło wyżej, {paired-up-down} pozostało na tym samym poziomie, a {down} przeszło niżej.', 10), Spacer(1, 6)]
        if paired >= 5 and up > down:
            candidates['K5'] = (.55, f'W porównywanej grupie awanse ({up}) były częstsze niż spadki ({down}).')
        if paired < 5:
            candidates['K8'] = (1.1, f'Porównanie obejmuje {paired} uczniów z kategorią w obu pomiarach.')
    if n and sum(overall[:2]) * 4 >= n and sum(overall[2:]) * 4 >= n:
        candidates['K6'] = (.52, f'W dwóch niższych kategoriach jest {sum(overall[:2])} z {n} uczniów, a w dwóch wyższych {sum(overall[2:])}.')
    if by_class:
        class_by_student = {row['student']: row['classroom'] for row in roster}
        classes = {}
        for row in records:
            level = row['levels'][8]
            if row['turn'] == latest and level is not None:
                classes.setdefault(class_by_student[row['student']], []).append(level)
        rates = [sum(level >= 2 for level in levels)/len(levels) for levels in classes.values() if len(levels) >= 10]
        if len(rates) >= 2 and max(rates)-min(rates) >= .2:
            candidates['K7'] = (.58, 'W klasach z co najmniej 10 kategoriami odsetki uczniów na poziomie co najmniej „Sprawny” różnią się o co najmniej 20 pkt proc.')
    if n < 5 or n * 5 < len(roster) * 4:
        candidates['K8'] = (1.1, f'W ostatnim pomiarze kategorię wyniku ogólnego ustalono dla {n} z {len(roster)} uczniów objętych raportem.')
    order = sorted(candidates, key=lambda item: -candidates[item][0])[:4]
    variant = 2 if by_class else 1
    options = tuple((item, TEACHER[item][variant]) for item in order)
    selected = model_choice(options) if use_ai else None
    if selected in order:
        order.remove(selected)
        order.insert(0, selected)
    if not order:
        items.append(paragraph('Wybierz obszar do dalszej obserwacji na podstawie wykresów i tego, co widzisz na lekcjach.', 10))
    for item in order:
        label, *_ = TEACHER[item]
        items += [Spacer(1, 6), card([paragraph(label, 12, GREEN), Spacer(1, 4),
                  paragraph(candidates[item][1], 9, MUTED), Spacer(1, 4),
                  paragraph(TEACHER[item][variant], 10)], WIDTH)]
    return items
