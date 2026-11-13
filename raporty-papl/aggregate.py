import io
from collections import Counter
from decimal import Decimal
from unicodedata import normalize
from statistics import mean
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Circle, Drawing, Line, Rect, String
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import KeepTogether, LongTable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

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

GUIDE = ('https://www.awf.edu.pl/__data/assets/pdf_file/0008/60479/'
         'e-book-Alfabet_ruchowy.-Przewodnik-dla-nauczycieli-i-rodzicow.pdf')
SCENARIOS = '30 scenariuszy zajęć WF wykorzystujących podstawowe umiejętności ruchowe (2026)'
TEACHER_MATERIALS = {
    'K1': (
        (f'{SCENARIOS}, scenariusz 25 „Wyzwania ruchowe. Łączenie umiejętności”, s. 291.', None),
        (f'{SCENARIOS}, cz. II „Weryfikacja efektów lekcji przez nauczyciela”, s. 361. '
         'Karty obserwacji umiejętności ruchowych.', None),
    ),
    'K2': (('Alfabet ruchowy (2024), „Zaangażowanie w całożyciową aktywność fizyczną”, s. 51.', 51),),
    'K3': (
        ('Alfabet ruchowy (2024), „Motywacja i pewność siebie”, s. 25.', 25),
        (f'{SCENARIOS}, „Ocena lekcji przez uczniów”, s. 382. '
         'Materiał do poznania opinii uczniów o zajęciach.', None),
    ),
    'K4': (('Alfabet ruchowy (2024), „Wiedza i zrozumienie”, s. 41.', 41),),
}


def material_paragraph(label, pdf_page):
    if pdf_page is None:
        return paragraph(label, 9, MUTED)
    item = paragraph(label, 9, GREEN)
    return Paragraph(f'<link href="{GUIDE}#page={pdf_page}"><u>{escape(label)}</u></link>', item.style)


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

def transitions(records, first, second, metric=8):
    by_turn = {
        turn:{r['student']:r['levels'][metric] for r in records if r['turn']==turn and r['levels'][metric] is not None}
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
    draw = Drawing(width, 34 if narrow else 52)
    draw.add(Rect(0, 17 if not narrow else 7, width, 15 if narrow else 17, fillColor=PAPER, strokeColor=None))
    if n:
        x = 0
        small_segments = []
        for count, color in zip(counts, BANDS):
            if not count:
                continue
            segment = width * count / n
            draw.add(Rect(x, 17 if not narrow else 7, segment, 15 if narrow else 17,
                          fillColor=color, strokeColor=None))
            value = percent(count, n)
            if segment >= stringWidth(value, 'PAPL', 8) + 6:
                draw.add(String(x + segment / 2, 23 if not narrow else 12, value, textAnchor='middle',
                                fontName='PAPL', fontSize=8, fillColor=INK))
            else:
                small_segments.append((color, value))
            x += segment
        x = 0
        baseline = 4 if not narrow else 0
        for color, value in small_segments:
            draw.add(Rect(x, baseline, 6, 5, fillColor=color, strokeColor=None))
            draw.add(String(x + 9, baseline, value, fontName='PAPL', fontSize=8, fillColor=MUTED))
            x += 16 + stringWidth(value, 'PAPL', 8)
        details = ''
    else:
        details = 'Brak kategorii PAPL w tym pomiarze'
    if details:
        draw.add(String(0, 5 if not narrow else 0, details, fontName='PAPL', fontSize=8, fillColor=MUTED))
    sample = f'n = {n}' + (f' · bez kategorii {available - n}' if available > n else '')
    draw.add(String(width, 39 if not narrow else 27, sample, textAnchor='end', fontName='PAPL', fontSize=8, fillColor=MUTED))
    label_width = width - stringWidth(sample, 'PAPL', 8) - 8
    short_label = label
    while short_label and stringWidth(short_label + ('…' if short_label != label else ''), 'PAPL', 9) > label_width:
        short_label = short_label[:-1]
    if short_label != label:
        short_label += '…'
    draw.add(String(0, 39 if not narrow else 27, short_label, fontName='PAPL', fontSize=9, fillColor=INK))
    return draw


def turn_label(turns, turn):
    if len(turns) == 1:
        return 'Aktualny pomiar'
    if turn == turns[0]:
        return 'Pierwszy pomiar'
    return 'Ostatni pomiar' if turn == turns[-1] else 'Drugi pomiar'


def charts(records, turns, metric, width):
    return [distribution_row(turn_label(turns, turn), *distribution(records, turn, metric), width)
            for turn in turns]


def proficiency_series(records, turns, metric):
    series = []
    for turn in turns:
        _, counts = distribution(records, turn, metric)
        n = sum(counts)
        series.append(sum(counts[2:]) / n if n else None)
    return series


def delta_text(series):
    if len(series) < 2 or series[0] is None or series[-1] is None:
        return 'Brak porównania'
    return f'{100 * (series[-1] - series[0]):+.1f}'.replace('.', ',') + ' p.p.'


def proficiency_chart(series, width, compact=False):
    height = (24 if compact else 36) if len(series) == 1 else (48 if compact else 105)
    draw = Drawing(width, height)
    latest = series[-1]
    label = f'{100 * latest:.1f}%'.replace('.', ',') if latest is not None else 'Brak danych'
    draw.add(String(0, height-16, label, fontName='PAPL', fontSize=15 if compact else 21, fillColor=GREEN))
    if len(series) > 1:
        draw.add(String(width, height-15, delta_text(series), textAnchor='end',
                        fontName='PAPL', fontSize=9, fillColor=MUTED))
    if len(series) == 1:
        return draw
    plot_height = 12 if compact else 40
    previous = None
    for i, share in enumerate(series):
        x = 20 + i*(width-40)/(len(series)-1)
        if share is None:
            previous = None
            draw.add(String(x, 3, 'Brak', textAnchor='middle', fontName='PAPL', fontSize=8, fillColor=MUTED))
            continue
        y = (13 if compact else 16) + plot_height * share
        if previous:
            draw.add(Line(*previous, x, y, strokeColor=GREEN, strokeWidth=1.4))
        draw.add(Circle(x, y, 2.6, fillColor=GREEN, strokeColor=None))
        draw.add(String(x, 3, f'{100 * share:.1f}%'.replace('.', ','), textAnchor='middle',
                        fontName='PAPL', fontSize=8, fillColor=MUTED))
        previous = (x, y)
    return draw


def student_progress(records, metric):
    histories = {}
    for row in records:
        if row['scores'][metric] is not None and row['levels'][metric] is not None:
            histories.setdefault(row['student'], []).append(row)
    counts = [0, 0, 0]
    large_up = large_down = score_up = 0
    for history in histories.values():
        if len(history) < 2:
            continue
        start = min(history, key=lambda row: row['turn'])
        end = max(history, key=lambda row: row['turn'])
        change = end['levels'][metric] - start['levels'][metric]
        counts[0 if change > 0 else 2 if change < 0 else 1] += 1
        large_up += change >= 2
        large_down += change <= -2
        score_up += change == 0 and end['scores'][metric] > start['scores'][metric]
    return counts, large_up, large_down, score_up


def progress_items(records, metric, width):
    counts, large_up, large_down, score_up = student_progress(records, metric)
    n = sum(counts)
    if not n:
        return [paragraph('Brak wyników do porównania u tych samych uczniów.', 9, MUTED)]
    colors = (GREEN, MUTED, HexColor('#A33B34'))
    draw = Drawing(width, 40)
    for i, (label, count, color) in enumerate(zip(('↑ Wyżej', '= Bez zmiany', '↓ Niżej'), counts, colors)):
        x = width * (i + .5) / 3
        draw.add(String(x, 29, label, textAnchor='middle', fontName='PAPL', fontSize=9, fillColor=color))
        draw.add(String(x, 17, f'{percent(count, n)} ({count})', textAnchor='middle',
                        fontName='PAPL', fontSize=9, fillColor=color))
    offset = 0
    for count, color in zip(counts, colors):
        segment = width * count/n
        if count:
            draw.add(Rect(offset, 3, segment, 7, fillColor=color, strokeColor=None))
        offset += segment
    trend = ('Więcej uczniów przeszło wyżej niż niżej.' if counts[0] > counts[2] else
             'Więcej uczniów przeszło niżej niż wyżej.' if counts[2] > counts[0] else
             'Liczba przejść w górę i w dół jest taka sama.' if counts[0] else
             'Wszyscy porównani uczniowie utrzymali kategorię.')
    items = [draw, paragraph(f'{trend} O ≥2 poziomy: {large_up} wyżej, {large_down} niżej.' if width < 250
                             else f'{trend} Porównano {n} uczniów. O ≥2 poziomy: {large_up} wyżej i {large_down} niżej.', 9)]
    if score_up and width > 250:
        items.append(paragraph(f'U {score_up} uczniów wynik punktowy wzrósł w tej samej kategorii.', 9))
    return items


def metric_section(records, turns, metric, series):
    distribution_card = card([paragraph('Rozkład poziomów', 13, GREEN), Spacer(1, 5),
                              *charts(records, turns, metric, 316)], 338)
    score_items = [paragraph('Co najmniej sprawni', 12, GREEN), proficiency_chart(series, 139),
                   paragraph('Średni wynik', 11, GREEN), Spacer(1, 4)]
    for turn in turns:
        values = [row['scores'][metric] for row in records if row['turn'] == turn and row['scores'][metric] is not None]
        result = f'{mean(values):.1f}'.replace('.', ',') + ' pkt' if values else 'Brak wyniku'
        score_items += [paragraph(f'{turn_label(turns, turn)} · n = {len(values)}', 8, MUTED),
                        paragraph(result, 13), Spacer(1, 7)]
    items = [grid([[distribution_card, '', card(score_items, 161)]], [338, 12, 161]), Spacer(1, 10)]
    if len(turns) > 1:
        items += [card([paragraph('Kierunek zmian u tych samych uczniów', 13, GREEN),
                        paragraph('Pierwszy i ostatni ważny pomiar każdego ucznia.', 9, MUTED),
                        *progress_items(records, metric, WIDTH-22)], WIDTH), Spacer(1, 7)]
    items += [paragraph('Słupki pokazują wszystkich uczniów z kategorią PAPL w danym pomiarze. Zmiany udziałów mogą częściowo wynikać ze zmiany składu grupy.', 9, MUTED)]
    return items


def student_tables(records, roster, turns):
    recent_turns = turns[-2:]
    last = recent_turns[-1]
    previous = recent_turns[0] if len(recent_turns) == 2 else None
    history = {(row['student'], row['turn']): row for row in records if row['turn'] in recent_turns}
    classes = {}
    for row in roster:
        classes.setdefault(row['classroom'], []).append(row)
    red = HexColor('#A33B34')
    directions = {1: ('↑ Poprawa', GREEN), 0: ('→ Bez zmian', MUTED), -1: ('↓ Pogorszenie', red)}

    def sort_key(row):
        def polish(value):
            return tuple((normalize('NFD', char)[0] if char != 'ł' else 'l', char != normalize('NFD', char)[0] or char == 'ł', char)
                         for char in value.casefold())
        return (polish(row.get('surname') or row['name']), polish(row.get('given_name', '')), row['student'])

    def measurement(row, metric):
        if row is None or row['scores'][metric] is None:
            return [paragraph('—', 10, MUTED)], None, None
        score = Decimal(str(row['scores'][metric]))
        level = row['levels'][metric]
        cells = [paragraph(format(score, '.1f').replace('.', ','), 10)]
        if level is not None:
            cells.append(paragraph(LEVELS[level], 8.5, MUTED))
        for cell in cells:
            cell.style.alignment = 2
        return cells, score, level

    def period(members, turn):
        dates = sorted({row['test'].strftime('%Y-%m-%d') for member in members
                        if (row := history.get((member['student'], turn))) and row.get('test')})
        if not dates:
            return 'brak dat w arkuszu' if turn is not None else '—'
        return dates[0] if len(dates) == 1 else f'{dates[0]} – {dates[-1]}'

    items = []
    for room, members in sorted(classes.items()):
        members = sorted(members, key=sort_key)
        for metric, label in METRICS:
            rows = [[paragraph(v, 9, GREEN) for v in
                     ('Nazwisko i imię', 'Poprzedni pomiar', 'Ostatni pomiar', 'Zmiana (pkt)', 'Kierunek')]]
            totals = Counter()
            for member in members:
                student = member['student']
                name = ' '.join(filter(None, (member.get('surname'), member.get('given_name')))) or member['name']
                earlier, old_score, old_level = measurement(history.get((student, previous)), metric)
                current, new_score, new_level = measurement(history.get((student, last)), metric)
                delta = '—'
                status = [paragraph('Brak porównania', 9, MUTED)]
                if old_score is not None and new_score is not None:
                    change = new_score - old_score
                    sign = (change > 0) - (change < 0)
                    totals[sign] += 1
                    delta = f'{change:+.1f}'.replace('.', ',') if sign else '0,0'
                    if sign and format(abs(change), '.1f') == '0.0':
                        delta = '+<0,1' if sign > 0 else '−<0,1'
                    direction, color = directions[sign]
                    status = [paragraph(direction, 10, color)]
                    if old_level is not None and new_level is not None:
                        category = ('↑ Kategoria wyższa' if new_level > old_level else
                                    '↓ Kategoria niższa' if new_level < old_level else 'Kategoria bez zmian')
                        status.append(paragraph(category, 8.5, MUTED))
                delta_cell = paragraph(delta, 10)
                delta_cell.style.alignment = 2
                rows.append([paragraph(name, 10), earlier, current, delta_cell, status])
            context = paragraph(f'Klasa {room} · {label} · {len(members)} uczniów', 11, GREEN)
            dates = paragraph(f'Poprzedni pomiar: {period(members, previous)} · Ostatni pomiar: {period(members, last)}', 9)
            table = LongTable([[context, '', '', '', ''], [dates, '', '', '', ''], *rows],
                              colWidths=[149, 86, 86, 67, 123], repeatRows=3, splitInRow=0, hAlign='LEFT')
            table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('SPAN', (0, 0), (-1, 0)), ('SPAN', (0, 1), (-1, 1)),
                ('BACKGROUND', (0, 2), (-1, 2), RULE),
                ('ROWBACKGROUNDS', (0, 3), (-1, -1), [white, PAPER]),
                ('LINEBELOW', (0, 0), (-1, -1), .3, RULE),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            missing = len(members) - sum(totals.values())
            items += [PageBreak(), paragraph('Indywidualne postępy uczniów', 15, GREEN),
                      Spacer(1, 6),
                      paragraph(f'Zmiany punktowe · ↑ Poprawa {totals[1]} · → Bez zmian {totals[0]} · ↓ Pogorszenie {totals[-1]} · Brak porównania {missing}', 9),
                      paragraph('Kierunek wynika z różnicy przed zaokrągleniem. Kategorię PAPL podano pod wynikiem, gdy jest dostępna.', 9, MUTED), Spacer(1, 8), table]
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
              Spacer(1, 6)]
    series = {metric: proficiency_series(records, turns, metric) for metric, _ in METRICS}
    current_share = series[8][-1]
    badges = [(str(len(roster)), 'Uczniowie w raporcie'),
              (percent(current_share, 1) if current_share is not None else 'Brak danych',
               'Co najmniej sprawni · ostatni pomiar')]
    if len(turns) > 1:
        progress_counts = student_progress(records, 8)[0]
        compared = sum(progress_counts)
        badges.append((percent(progress_counts[0], compared) if compared else 'Brak danych',
                       f'Wyższa kategoria · n = {compared}'))
    gap = 8
    badge_width = (WIDTH - gap * (len(badges) - 1)) / len(badges)
    badge_row, badge_widths = [], []
    for value, label in badges:
        if badge_row:
            badge_row.append('')
            badge_widths.append(gap)
        badge_row.append(grid([[[paragraph(value, 16, GREEN), paragraph(label, 9, MUTED)]]],
                              [badge_width], card=True, padding=7))
        badge_widths.append(badge_width)
    items += [grid([badge_row], badge_widths), Spacer(1, 5), legend()]
    items += metric_section(records, turns, 8, series[8])
    observed = [(values[-1], label) for metric, label in METRICS[1:]
                if (values := series[metric])[-1] is not None]
    if observed:
        low, high = min(observed), max(observed)
        items += [Spacer(1, 10), paragraph('Najważniejsze wnioski', 12, GREEN),
                  paragraph(f'Największy udział uczniów na poziomie co najmniej „Sprawny” odnotowano w obszarze „{high[1]}”.'
                            + (f' Najmniejszy udział odnotowano w obszarze „{low[1]}”.' if high[0] != low[0] else ''), 10)]

    changes_by_domain = [(values[-1]-values[0], label) for metric, label in METRICS[1:]
                         if len(values := series[metric]) > 1 and values[0] is not None and values[-1] is not None]
    if changes_by_domain:
        best, worst = max(changes_by_domain), min(changes_by_domain)
        if best[0] > 0:
            items.append(paragraph(f'Największy wzrost udziału · {best[1]}', 10, GREEN))
        if worst[0] < 0:
            items.append(paragraph(f'Największy spadek udziału · {worst[1]}', 10))
        elif 0 <= worst[0] < best[0]:
            items.append(paragraph(f'Najmniejsza zmiana udziału · {worst[1]}', 10))


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
    for metric, label in METRICS[1:]:
        items += [KeepTogether([Spacer(1, 12), *heading(label), legend(),
                  *metric_section(records, turns, metric, series[metric])])]

    if comparison:
        items += [PageBreak(), *heading(f'Porównanie klas · {TURNS[turns[-1]]}'), legend()]
        items += [KeepTogether([card([row], WIDTH), Spacer(1, 3)]) for row in comparison]

    items += [PageBreak(), *heading('Co wyniki podpowiadają do dalszej pracy?'),
              *teacher_feedback(records, roster, turns, by_class, use_ai),
              *student_tables(records, roster, turns)]

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
    if 'K1' not in candidates:
        _, camsa = distribution(records, latest, 0)
        camsa_n = sum(camsa)
        camsa_low = sum(camsa[:2])
        if camsa_n and camsa_low * 2 >= camsa_n:
            candidates['K1'] = (camsa_low / camsa_n,
                                f'CAMSA. Dwie niższe kategorie obejmują {camsa_low} z {camsa_n} uczniów '
                                f'({percent(camsa_low, camsa_n)}).')
    if len(turns) > 1:
        first = turns[-2]
        counts = transitions(records, first, latest)
        up = sum(v for (a, b), v in counts.items() if b > a)
        down = sum(v for (a, b), v in counts.items() if b < a)
        paired = sum(counts.values())
        for metric, label in METRICS[1:]:
            domain_counts = transitions(records, first, latest, metric)
            domain_n = sum(domain_counts.values())
            if not domain_n:
                continue
            gained = sum(v for (a, b), v in domain_counts.items() if b > a)
            lost = sum(v for (a, b), v in domain_counts.items() if b < a)
            key = f'K{metric-3}'
            if domain_n >= 5 and lost > gained:
                _, latest_counts = distribution(records, latest, metric)
                low_share = sum(latest_counts[:2]) / sum(latest_counts)
                candidates[key] = (1 + (lost-gained)/domain_n + low_share,
                                   f'{label}. Wśród {domain_n} uczniów porównanych w obu pomiarach {lost} przeszło niżej, a {gained} wyżej.')
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
    teaching_priorities = [key for key in ('K1', 'K2', 'K3', 'K4') if key in candidates]
    priority = max(teaching_priorities, key=lambda key: candidates[key][0]) if teaching_priorities else None
    strong = 'Brak danych o poziomach w domenach w ostatnim pomiarze.'
    if strengths:
        _, label, high, size = max(strengths)
        strong = (f'Najwyższy odsetek na poziomie co najmniej „Sprawny” odnotowano w obszarze „{label}” ({high} z {size}).'
                  if high else 'W dostępnych domenach warto poszukać postępów poszczególnych uczniów w tabelach wyników.')
    if len(turns) > 1 and up > down:
        strong += f' W wyniku ogólnym odnotowano więcej awansów niż spadków kategorii ({up} wobec {down}).'
    focus = candidates[priority][1] if priority else 'Wybierzcie obszar do obserwacji na podstawie wyników i przebiegu zajęć.'
    if len(turns) > 1 and down > up:
        focus += f' W wyniku ogólnym odnotowano więcej spadków niż awansów kategorii ({down} wobec {up}).'
    items = [grid([[card([paragraph('Mocne strony', 12, GREEN), Spacer(1, 4), paragraph(strong, 10)], 249),
                    '', card([paragraph('Do doskonalenia', 12, GREEN), Spacer(1, 4), paragraph(focus, 10)], 249)]],
                  [249, 13, 249]), Spacer(1, 12), paragraph('Rekomendacje dla nauczyciela', 13, GREEN)]
    order = sorted(candidates, key=lambda item: -candidates[item][0])[:3]
    variant = 2 if by_class else 1
    options = tuple((item, TEACHER[item][variant]) for item in order if item != priority)
    selected = model_choice(options) if use_ai else None
    leading = [item for item in (priority, selected) if item]
    order = (leading + [item for item in order if item not in leading])[:3]
    if not order:
        items.append(paragraph('Wybierz obszar do dalszej obserwacji na podstawie wykresów i tego, co widzisz na lekcjach.', 10))
    material_priority = next((item for item in order if item in TEACHER_MATERIALS), None)
    for item in order:
        label, *_ = TEACHER[item]
        if item == priority:
            label = 'Priorytet do pracy · ' + label
        advice = TEACHER[item][variant]
        content = [paragraph(label, 12, GREEN), Spacer(1, 4),
                   paragraph(candidates[item][1], 9, MUTED), Spacer(1, 4),
                   paragraph(advice, 10)]
        if item == material_priority:
            content += [Spacer(1, 6), paragraph('Materiały do wykorzystania', 10, GREEN)]
            for reference, pdf_page in TEACHER_MATERIALS[item]:
                content += [Spacer(1, 3), material_paragraph(reference, pdf_page)]
        items += [Spacer(1, 6), card(content, WIDTH)]
    return items
