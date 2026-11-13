import json
import os
from functools import lru_cache
from urllib.request import Request, urlopen

LEVELS = ('Początkujący', 'Dokonujący postępów', 'Sprawny', 'Wyróżniający się')
CHILD = {
    'OG1': 'Pomyśl, jaka zabawa w ruchu sprawia Ci przyjemność. Wybierz jeden dzień w tym tygodniu, kiedy chcesz do niej wrócić.',
    'OG2': 'Wybierz jedną rzecz, której chcesz spróbować w ruchu. Może to być zabawa, którą już znasz, albo coś nowego. Po zabawie pomyśl, co chcesz powtórzyć.',
    'AK1': 'Wybierz moment w ciągu dnia, kiedy masz ochotę się poruszać. Na przykład po szkole zaproś kogoś na krótki spacer albo pobaw się na dworze.',
    'AK2': 'Pomyśl, kiedy w tym tygodniu znajdziesz chwilę na spacer albo zabawę w ruchu. Możesz wybrać się z kimś bliskim i razem zdecydować, dokąd pójdziecie.',
    'AK3': 'Przypomnij sobie zabawę albo wyjście, podczas których było dużo ruchu. Jeśli Ci się podobało, znajdź w tym tygodniu okazję, żeby to powtórzyć.',
    'RU1': 'Wybierz zabawę, w której możesz poćwiczyć coś, co Cię ciekawi. Możesz rzucać piłką do celu, przeskakiwać przez linie albo wymyślić własny tor przeszkód.',
    'RU2': 'Wymyśl krótki tor z trzema zadaniami. Przejdź po linii, przeskocz przez nią i rzuć piłką do celu. Potem zmień jedno zadanie i sprawdź, która wersja bardziej Ci się podoba.',
    'RU3': 'Wróć do zabawy ruchowej, którą lubisz. Jeśli masz ochotę na małe wyzwanie, zmień jedną rzecz, na przykład rzuć piłką z trochę większej odległości.',
    'MP1': 'Wybierz zabawę, w której czujesz się swobodnie. Możesz zaprosić kogoś, z kim lubisz spędzać czas, i razem ustalić zasady.',
    'MP2': 'Pomyśl o zabawie ruchowej, której chcesz spróbować. Zacznij od jednej prostej rzeczy, na przykład od rzucania piłką z bliska.',
    'WI1': 'Podczas spaceru albo zabawy zwróć uwagę, kiedy oddychasz szybciej. Opowiedz komuś, przy jakim ruchu to zauważasz.',
    'WI2': 'Wybierz zabawę i wytłumacz komuś jej zasady. Potem wymyślcie jedną zmianę, dzięki której więcej osób będzie mogło się z Wami bawić.',
    'MI1': 'Wybierz jedną rzecz, którą chcesz dalej ćwiczyć. Po kilku próbach sprawdź, co przychodzi Ci łatwiej albo sprawia Ci więcej przyjemności.',
}

TEACHER = {
    'K1': ('Kompetencje fizyczne',
           'Na podstawie prób i obserwacji wybierz jedną umiejętność, np. chwyt lub lądowanie. Wracaj do niej przez kilka lekcji w różnych zabawach. Sprawdź w podobnym zadaniu, czy uczniowie częściej wykonują wybrany element poprawnie.',
           'Uzgodnijcie jedną umiejętność do rozwijania w kilku klasach i wspólny sposób obserwacji. Po kilku tygodniach wymieńcie się zadaniami, które sprawdziły się na lekcjach.'),
    'K2': ('Okazje do ruchu w ciągu dnia',
           'Zapytaj uczniów, kiedy mają okazję się ruszać i co im to utrudnia. Wypróbujcie jedną zabawę na przerwie. Po dwóch tygodniach sprawdźcie, kto z niej korzysta i co ułatwiłoby udział pozostałym.',
           'Sprawdźcie dostęp klas do miejsca i sprzętu na przerwach. Wypróbujcie jedną formę aktywnej przerwy i zapytajcie uczniów, co ułatwia im udział.'),
    'K3': ('Motywacja i pewność siebie',
           'Daj uczniom wybór wersji zadania i możliwość samodzielnego przejścia do trudniejszej próby. Obserwuj, czy uczniowie rzadziej podejmujący zadania częściej się włączają.',
           'Zapytajcie uczniów, co zachęca ich do udziału w WF. W kilku klasach przetestujcie jedną zmianę, np. wybór zadań, i porównajcie obserwacje nauczycieli.'),
    'K4': ('Wiedza w praktyce',
           'Po zabawie zapytaj, po czym uczniowie poznają, że ruch jest intensywniejszy. Na kolejnej lekcji sprawdź, czy wykorzystują tę obserwację, dobierając tempo.',
           'Uzgodnijcie kilka krótkich pytań po zadaniach ruchowych. Porównajcie odpowiedzi uczniów przed cyklem zajęć i po nim.'),
    'K5': ('Kontynuacja pracy',
           'Wybierz jedno zadanie z ostatnich lekcji i sprawdź, czy uczniowie wykorzystują ćwiczoną umiejętność także w innej zabawie.',
           'Zbierzcie przykłady zadań i sposobów organizacji lekcji. Wypróbujcie jedno rozwiązanie w kolejnej klasie i porównajcie obserwacje.'),
    'K6': ('Zadania o różnej trudności',
           'Przygotuj kilka wariantów wspólnego zadania. Sprawdź, czy każdy uczeń ma okazję wykonać kilka udanych prób i może wybrać kolejne wyzwanie.',
           'Przygotujcie warianty często używanych zadań i sprawdźcie, czy da się je przeprowadzić w różnych salach z dostępnym sprzętem.'),
    'K7': ('Porównanie klas',
           'Zestaw wynik klasy z obserwacjami na lekcji. Sprawdź na przykład, ile prób wykonują uczniowie podczas pracy na stacjach.',
           'Omówcie wyniki klas z uwzględnieniem liczebności, braków i warunków zajęć. Wybierzcie jedną praktykę do wspólnego wypróbowania i ustalcie, co będziecie obserwować.'),
    'K8': ('Kompletność wyników',
           'Sprawdź, których pomiarów brakuje i co można uzupełnić. Dobierając zadania, uwzględnij też obserwacje uczniów podczas lekcji.',
           'Sprawdźcie, na którym etapie powstają braki. Ustalcie, które dane można uzupełnić i kto sprawdzi kompletność przed kolejną turą.'),
}


@lru_cache(maxsize=128)
def model_choice(options):
    key = os.getenv('OPENAI_API_KEY')
    if not key or len(options) < 2:
        return None
    # Only approved text and its ID leave the application.
    payload = {
        'model': os.getenv('PAPL_OPENAI_MODEL') or 'gpt-4.1-mini',
        'store': False,
        'max_output_tokens': 48,
        'instructions': 'Wybierz jedną najprostszą do wypróbowania wskazówkę z listy. Zwróć wyłącznie jej identyfikator.',
        'input': json.dumps(options, ensure_ascii=False),
    }
    request = Request('https://api.openai.com/v1/responses', json.dumps(payload).encode(),
                      {'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    try:
        with urlopen(request, timeout=2) as response:
            result = json.load(response)
        value = ''.join(part.get('text', '') for item in result.get('output', [])
                        for part in item.get('content', []) if part.get('type') == 'output_text').strip()
        if value in dict(options):
            return value
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return None


def child_feedback(records, norms, keys, fmt, use_ai=True):
    recent = records[-1]
    overall = [row for row in records if row['scores'][8] is not None]
    notes = []
    candidates = ('OG1', 'OG2')
    if recent['scores'][8] is None:
        notes.append('W najnowszym badaniu brakuje wyniku łącznego.')
    if overall:
        current = overall[-1]
        level = current['levels'][8]
        when = 'W najnowszym badaniu' if current is recent else 'We wcześniejszym badaniu'
        notes.append(f'{when} udało Ci się zdobyć {fmt(current["scores"][8])} na 100 punktów.')
        if level is not None:
            notes.append(f'Ten wynik mieści się na poziomie „{LEVELS[level]}”.')
    if len(overall) > 1:
        previous = overall[-2]
        points = [fmt(row['scores'][8]) for row in overall]
        if len(points) == 3:
            notes.append(f'Twoje wyniki w kolejnych badaniach to {points[0]}, {points[1]} i {points[2]} pkt.')
        else:
            notes.append(f'Wcześniejszy wynik to {points[0]} pkt.')
        old_level, new_level = previous['levels'][8], current['levels'][8]
        if old_level is not None and new_level is not None and old_level != new_level:
            previous_direction = 'niższy' if new_level > old_level else 'wyższy'
            notes.append(f'W poprzednim badaniu z wynikiem łącznym poziom był {previous_direction} („{LEVELS[old_level]}”).')
            old_norm = norms.get((previous['sex'], previous['age'], keys[8]))
            new_norm = norms.get((current['sex'], current['age'], keys[8]))
            if new_level < old_level and current['scores'][8] > previous['scores'][8]:
                candidates = ('MI1',)
                if old_norm and new_norm and new_norm[old_level] > old_norm[old_level]:
                    notes.append('Przybyło Ci punktów, a do osiągnięcia poprzedniego poziomu w ostatnim badaniu potrzeba ich było więcej.')
        elif old_level is not None and old_level == new_level:
            notes.append('W dwóch ostatnich badaniach z wynikiem łącznym poziom pozostał ten sam.')

    steps = [row for row in records if row['scores'][3] is not None]
    if len(notes) < 5 and len(steps) > 1 and steps[-1] is recent and steps[-1]['scores'][3] != steps[-2]['scores'][3]:
        lower = steps[-1]['scores'][3] < steps[-2]['scores'][3]
        direction = 'niższa' if lower else 'wyższa'
        notes.append(f'W ostatnim badaniu średnia liczba kroków dziennie była {direction} niż przy poprzednim pomiarze kroków.')
        candidates = ('AK2', 'AK1') if lower else ('AK3',)
    elif len(notes) < 5:
        labels = {4:'umiejętności w zadaniach ruchowych', 5:'ruchu na co dzień',
                  6:'chęci do ruchu i pewności siebie', 7:'wiedzy o ruchu'}
        available = [idx for idx in labels if recent['levels'][idx] is not None]
        if available:
            idx = min(available, key=lambda idx: recent['levels'][idx])
            domain_level = recent['levels'][idx]
            notes.append(f'W części dotyczącej {labels[idx]} Twój wynik jest na poziomie „{LEVELS[domain_level]}”.')
            if candidates[0] == 'OG1' and domain_level < 2:
                candidates = {4:('RU2', 'RU1') if recent['levels'][0] in (0, 1) else ('RU1',),
                              5:('AK1',), 6:('MP1', 'MP2'), 7:('WI1', 'WI2')}[idx]
        elif not overall:
            notes.append('Na wykresach możesz zobaczyć, jak poszło Ci w poszczególnych zadaniach.')
    options = tuple((item, CHILD[item]) for item in candidates)
    selected = model_choice(options) if use_ai else None
    return ' '.join(notes), CHILD[selected or candidates[0]]
