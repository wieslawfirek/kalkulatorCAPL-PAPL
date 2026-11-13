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


LEVEL_MEANINGS = (
    'To punkt wyjścia do ćwiczenia podstaw. Możesz zacząć od prostych prób i poprosić o pomoc, gdy jej potrzebujesz.',
    'Masz już podstawy, które możesz utrwalać w różnych zabawach i zadaniach.',
    'Twój wynik osiąga poziom sprawności określony w normach dla Twojego wieku. Możesz wykorzystać to, co już Ci wychodzi, w nowych zadaniach.',
    'To najwyższa kategoria wyniku w tym badaniu. Możesz wykorzystać swoje mocne strony, podejmując nowe wyzwania w ruchu.',
)

CHILD_DOMAINS = {
    4: ('Zadania ruchowe', 'Ta część pokazuje, jak poszło Ci w różnych zadaniach ruchowych.',
        'Ustaw kosz i spróbuj wrzucić do niego pięć zwiniętych skarpetek. Innym razem rzuć z tego samego miejsca i zobacz, czy uda Ci się trafić częściej.'),
    5: ('Ruch na co dzień', 'Ta część dotyczy ruchu w zwykłe dni, także poza lekcjami WF.',
        'Zastanów się, kiedy najłatwiej znaleźć chwilę na ruch, który lubisz.'),
    6: ('Motywacja do ruchu i pewność siebie', 'Tutaj liczą się Twoje odpowiedzi na pytania o to, jak odbierasz ruch i jak się w nim czujesz.',
        'Pomyśl, w jakiej zabawie czujesz się swobodnie i czego chcesz spróbować następnym razem.'),
    7: ('Wiedza o ruchu', 'W tej części liczą się Twoje odpowiedzi na pytania o ruch.',
        'Możesz wykorzystać tę wiedzę w zabawie, na przykład zauważyć, jak zmienia się oddech, gdy zmieniasz tempo.'),
}

CHILD_TRIALS = {
    0: ('w teście umiejętności ruchowych', 'udało Ci się zdobyć więcej punktów'),
    1: ('w biegu wahadłowym', 'udało Ci się ukończyć więcej odcinków'),
    2: ('w desce', 'udało Ci się dłużej utrzymać pozycję'),
    3: ('w pomiarze kroków', 'średnia dzienna liczba kroków wzrosła'),
}


def child_feedback(records, norms, keys, fmt, use_ai=True):
    recent = records[-1]
    available = {
        idx: [row for row in records if row['scores'][idx] is not None]
        for idx in range(9)
    }

    def trajectory(history, idx):
        if len(history) < 2:
            return ''
        values = [row['scores'][idx] for row in history]
        if len(values) == 3:
            if values[0] < values[1] > values[2]:
                return ' Wynik najpierw wzrósł, a w ostatnim badaniu był niższy.'
            if values[0] > values[1] < values[2]:
                return ' Wynik najpierw się obniżył, a w ostatnim badaniu wzrósł. To krok naprzód!'
        if values[-1] > values[-2]:
            return ' W ostatnim dostępnym badaniu wynik się poprawił. To postęp, który warto zauważyć!'
        if values[-1] < values[-2]:
            return ' W ostatnim dostępnym badaniu wynik był niższy niż poprzednio.'
        return ' W dwóch ostatnich dostępnych badaniach wynik pozostał taki sam.'

    def category_change(history, idx):
        if len(history) < 2:
            return ''
        previous, current = history[-2:]
        old, new = previous['levels'][idx], current['levels'][idx]
        if old is None or new is None:
            return ''
        if old == new:
            return ' W dwóch ostatnich dostępnych pomiarach poziom był taki sam.' if idx == 8 else ''
        return f' W poprzednim dostępnym pomiarze wynik był na poziomie „{LEVELS[old]}”.'

    def current_result(idx, maximum):
        current = available[idx][-1]
        when = 'W najnowszym badaniu' if current is recent else 'W ostatnim badaniu z wynikiem w tej części'
        level = current['levels'][idx]
        text = f'{when} Twój wynik to {fmt(current["scores"][idx])} na {maximum} punktów.'
        if level is not None:
            text += f' Mieści się na poziomie „{LEVELS[level]}”.'
        return text

    overall = available[8]
    introduction = ''
    if recent['scores'][8] is None:
        introduction = 'Z najnowszego badania mamy wyniki poszczególnych części. Brakuje wyniku łącznego. '
    if overall:
        introduction += current_result(8, 100)
        current = overall[-1]
        level = current['levels'][8]
        if level is not None:
            introduction += ' ' + LEVEL_MEANINGS[level]
        introduction += trajectory(overall, 8) + category_change(overall, 8)
        if len(overall) > 1:
            previous = overall[-2]
            old = previous['levels'][8]
            earlier_norm = norms.get((previous['sex'], previous['age'], keys[8]))
            latest_norm = norms.get((current['sex'], current['age'], keys[8]))
            if (old is not None and level is not None and 0 < old and level < old
                    and current['scores'][8] > previous['scores'][8] and earlier_norm and latest_norm):
                old_threshold, new_threshold = earlier_norm[old], latest_norm[old]
                old_rounded = round(current['scores'][8], earlier_norm[0])
                clears_old = old_rounded >= old_threshold if old == 1 else old_rounded > old_threshold
                if clears_old and new_threshold > old_threshold:
                    introduction += ' Punktów jest więcej, a do poprzedniego poziomu w tym badaniu potrzeba było wyższego wyniku.'
    sections = [('', introduction.strip())]
    for idx, (title, meaning, suggestion) in CHILD_DOMAINS.items():
        history = available[idx]
        trials = [trial for trial in ((1, 2, 0) if idx == 4 else (3,) if idx == 5 else ())
                  if available[trial]]
        if not history and not trials:
            continue
        text = meaning if history else ''
        if history:
            text += ' ' + current_result(idx, 10 if idx == 7 else 30)
            text += trajectory(history, idx) + category_change(history, idx)
        for trial in trials:
            trial_history = available[trial]
            if len(trial_history) < 2:
                continue
            previous, last = trial_history[-2:]
            name, achievement = CHILD_TRIALS[trial]
            if last['scores'][trial] > previous['scores'][trial]:
                text += f' Brawo! W ostatniej dostępnej próbie {name} {achievement}.'
            elif last['scores'][trial] < previous['scores'][trial]:
                text += (' W ostatniej dostępnej próbie deski pozycję udało Ci się utrzymać krócej niż wcześniej.'
                         if trial == 2 else f' W ostatniej dostępnej próbie {name} wynik był niższy niż wcześniej.')
            else:
                text += f' Wynik {name} pozostał taki sam.'
        if not history and not text:
            text = 'Kolejna próba pozwoli zobaczyć, jak zmieni się Twój wynik w tej części.'
        if history:
            level = history[-1]['levels'][idx]
            if level == 0:
                text += ' Zacznij od łatwiejszej wersji zabawy, którą chcesz wypróbować.'
            elif level == 1:
                text += ' To dobry punkt wyjścia do utrwalania tego, co już Ci wychodzi.'
            text += ' ' + suggestion
        sections.append((title, text.strip()))

    latest_domains = [idx for idx in CHILD_DOMAINS if recent['scores'][idx] is not None
                      and recent['levels'][idx] is not None]
    strengths = [idx for idx in latest_domains if recent['levels'][idx] >= 2]
    needs = [idx for idx in latest_domains if recent['levels'][idx] < 2]
    target = min(needs, key=lambda idx: recent['levels'][idx]) if needs else None
    progress = next((idx for idx in (1, 2, 0, 7, 4, 3, 5, 6, 8)
                     if len(available[idx]) >= 2 and available[idx][-1] is recent
                     and fmt(recent['scores'][idx]) != fmt(available[idx][-2]['scores'][idx])
                     and recent['scores'][idx] > available[idx][-2]['scores'][idx]), None)
    notes = []
    if progress is not None:
        achievement = {
            0: 'w teście umiejętności ruchowych udało Ci się zdobyć więcej punktów',
            1: 'w biegu wahadłowym udało Ci się ukończyć więcej odcinków',
            2: 'w desce udało Ci się dłużej utrzymać pozycję',
            3: 'w dniach najnowszego pomiaru średnia dzienna liczba kroków była większa',
            4: 'Twój wynik w zestawie zadań ruchowych wzrósł',
            5: 'Twój wynik w części o codziennym ruchu wzrósł',
            6: 'Twój wynik odpowiedzi o motywacji do ruchu i pewności siebie wzrósł',
            7: 'w odpowiedziach na pytania o ruch udało Ci się zdobyć więcej punktów',
            8: 'Twój wynik ogólny wzrósł',
        }
        notes.append(f'Zauważ swój postęp. W porównaniu z poprzednim dostępnym pomiarem {achievement[progress]}.')
    if strengths:
        best = max(strengths, key=lambda idx: recent['levels'][idx])
        notes.append(f'Twoja mocna strona w tym badaniu to obszar „{CHILD_DOMAINS[best][0]}”.')
    if not strengths and latest_domains:
        best = max(latest_domains, key=lambda idx: recent['levels'][idx])
        if recent['levels'][best] > min(recent['levels'][idx] for idx in latest_domains):
            notes.append(f'Wśród ocenionych obszarów najwyższy poziom ma Twój wynik w części „{CHILD_DOMAINS[best][0]}”.')
    if target is not None:
        notes.append(f'Jeśli chcesz wybrać jeden obszar do dalszej pracy, zacznij od „{CHILD_DOMAINS[target][0]}”.')
    if notes:
        sections.append(('Co warto zapamiętać?', ' '.join(notes)))

    candidates = {
        4: ('RU2', 'RU1'), 5: ('AK1', 'AK2'), 6: ('MP1', 'MP2'), 7: ('WI1', 'WI2'),
    }.get(target, ('OG1', 'OG2'))
    options = tuple((item, CHILD[item]) for item in candidates)
    selected = model_choice(options) if use_ai else None
    focus = {
        4: 'Skup się na jednej umiejętności wybranej wspólnie z dzieckiem. Jeśli wybierze rzut, zacznijcie od miękkiej piłki i bliskiego celu. Po kilku zabawach wróćcie do tego samego zadania i zauważcie, co dziecku wychodzi łatwiej.',
        5: 'Skup się na okazjach do ruchu w zwykłym dniu. Wybierzcie stały moment, na przykład po szkole, oraz aktywność, na którą dziecko ma ochotę. Po tygodniu zapytaj, które dni i zabawy najlepiej pasowały do waszego planu.',
        6: 'Skup się na tym, żeby dziecko mogło podjąć próbę na własnych warunkach. Daj mu wybrać zabawę, towarzystwo i łatwiejszą wersję zadania. Zauważ konkretnie, kiedy zaczęło, wróciło do próby lub samo wybrało trudniejszą wersję.',
        7: 'Skup się na wykorzystaniu wiedzy w zabawie. Po spacerze lub grze zapytaj, kiedy oddech przyspieszył i jak można zmienić tempo. Przy następnej zabawie pozwól dziecku wybrać tempo i opowiedzieć, dlaczego takie wybrało.',
    }.get(target, 'Zapytaj dziecko, co w raporcie zwróciło jego uwagę. Wybierzcie jedną zabawę, do której chce wrócić, i umówcie się, kiedy jej spróbujecie.')
    if progress is not None:
        focus += ' Wróćcie też do postępu wskazanego w części „Co warto zapamiętać?” i nazwijcie razem, co się poprawiło.'
    return sections, CHILD[selected or candidates[0]], focus
