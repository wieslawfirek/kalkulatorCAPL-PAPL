import json
import os
from functools import lru_cache
from urllib.request import Request, urlopen
from ai_narrative import generate_narrative

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
    'K1': ('Kompetencje ruchowe',
           'Skup się na podstawowych umiejętnościach ruchowych, które według obserwacji wymagają wsparcia. Zwróć uwagę, czy uczniowie wykonują je coraz pewniej i samodzielniej.',
           'Ustalcie wspólny priorytet w rozwijaniu podstawowych umiejętności ruchowych. Obserwujcie, czy w kolejnych klasach rośnie samodzielność uczniów w wybranym obszarze.'),
    'K2': ('Okazje do ruchu w ciągu dnia',
           'Zwiększaj dostępność regularnych okazji do ruchu dla uczniów, którzy rzadziej z nich korzystają. Zwróć uwagę, czy ruch w ciągu dnia staje się dla nich łatwiej dostępny.',
           'Skupcie się na dostępności okazji do ruchu w całym dniu szkolnym. Sprawdźcie, czy uczniowie różnych klas mogą korzystać z nich regularnie.'),
    'K3': ('Motywacja i pewność siebie',
           'Wzmacniaj poczucie, że każdy uczeń może robić postępy we własnym tempie. Obserwuj, czy osoby mniej pewne siebie chętniej podejmują próby i wracają do zadań.',
           'Wzmacniajcie warunki, w których uczniowie o różnym poziomie sprawności mogą uczestniczyć i dostrzegać swoje postępy. Zwróćcie uwagę na udział osób mniej pewnych siebie.'),
    'K4': ('Wiedza w praktyce',
           'Rozwijaj umiejętność korzystania z wiedzy o ruchu podczas zajęć. Sprawdzaj, czy uczniowie potrafią wyjaśnić własne wybory i zastosować wiedzę w nowej sytuacji.',
           'Ustalcie wspólne cele w zakresie rozumienia ruchu i korzystania z tej wiedzy. Obserwujcie, jak samodzielnie uczniowie stosują ją w różnych sytuacjach.'),
    'K5': ('Utrwalanie postępów',
           'Wzmacniaj obszar, w którym widać postęp. Zwróć uwagę, czy poprawa utrzymuje się w kolejnych pomiarach i jest widoczna w różnych sytuacjach ruchowych.',
           'Sprawdźcie, w których klasach postęp się utrzymuje. Uwzględnijcie różnice w warunkach zajęć i w grupach objętych pomiarem.'),
    'K6': ('Dopasowanie trudności',
           'Dopasowuj wymagania do zróżnicowanych możliwości uczniów. Obserwuj, czy każdy może wykonać zadanie na dostępnym dla siebie poziomie i stopniowo podejmować większe wyzwania.',
           'Ustalcie, gdzie zróżnicowanie wyników wymaga większego wsparcia. Zwróćcie uwagę, czy w każdej klasie uczniowie mają możliwość pracy na odpowiednim poziomie.'),
    'K7': ('Różnice między klasami',
           'Zestaw wyniki klasy z obserwacjami z lekcji, żeby określić, które potrzeby uczniów wymagają dalszej uwagi.',
           'Przyjrzyjcie się różnicom między klasami z uwzględnieniem liczebności, kompletności wyników i warunków zajęć. Na tej podstawie ustalcie, gdzie wsparcie jest najpilniejsze.'),
    'K8': ('Kompletność wyników',
           'Sprawdź, których uczniów obejmują porównania. Wnioski o potrzebach całej klasy uzupełnij obserwacjami z lekcji.',
           'Ustalcie, których klas i pomiarów dotyczą braki. Zadbajcie o porównywalny udział uczniów w kolejnych pomiarach.'),
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


# Approved fixed copy for individual reports. No external model is called here.
INDIVIDUAL_COPY_VERSION = '2026-11-19-fixed-v1'
PARENT_TEXT = ('Warto pamiętać, że {name} potrzebuje okazji do ruchu, życzliwego wsparcia i możliwości wyboru. '
               'Doceniajcie podejmowane próby, wysiłek i małe osiągnięcia, które rzeczywiście obserwujecie. '
               'Pytajcie, co sprawia dziecku przyjemność, i szukajcie dostępnych form wspólnej aktywności. '
               'Wynik raportu może być punktem wyjścia do rozmowy z dzieckiem i nauczycielem.')
OVERALL_TEXT = (
    'Wynik wskazuje na potrzebę wsparcia w rozwijaniu kompetencji potrzebnych do podejmowania różnorodnych aktywności fizycznych. Kategoria opisuje rezultat badania, a nie możliwości dziecka na przyszłość.',
    'Wynik wskazuje na rozwijające się podstawy alfabetu ruchowego oraz obszary, które warto dalej wspierać. Nazwa kategorii opisuje poziom wyniku; sama w sobie nie oznacza poprawy względem wcześniejszego badania.',
    'Wynik wskazuje na dobrze rozwinięte podstawy alfabetyzacji ruchowej w zakresie objętym badaniem PAPL.',
    'Jest to najwyższa kategoria w badaniu PAPL. Wynik wskazuje na bardzo dobrze rozwinięte podstawy alfabetyzacji ruchowej w zakresie objętym badaniem.',
)
CHILD_ENDINGS = (
    'Pamiętaj, że Twoja podróż z alfabetem ruchowym trwa przez całe życie. Zdobywając nowe doświadczenia, możesz krok po kroku rozwijać swoje umiejętności i pewność siebie. Każda podejmowana aktywność może wspierać Twoje zdrowie, dobre samopoczucie i dalszy rozwój. Ważna jest także radość z ruchu.',
    'Pamiętaj, że Twoja podróż z alfabetem ruchowym trwa przez całe życie. Opiera się na zdobywaniu nowych doświadczeń, emocjach, codziennych wyborach i radości z ruchu. Kontynuuj tę podróż — każda podejmowana aktywność może wspierać Twoje zdrowie, dobre samopoczucie i dalszy rozwój.',
    'Twoja podróż z alfabetem ruchowym trwa przez całe życie. Masz już dobre podstawy do jej dalszego rozwijania — odkrywaj nowe formy aktywności i podejmuj kolejne wyzwania. Swoją postawą możesz inspirować koleżanki i kolegów, pokazując, że ruch jest źródłem zdrowia, radości i satysfakcji.',
)
PROFILE_DOMAINS = ((5, 'zachowania codzienne'), (4, 'kompetencje ruchowe'),
                   (6, 'motywacja i pewność siebie'), (7, 'wiedza i zrozumienie'))


# Fixed report copy. The category interpretation is supplied by the report author.
GENERAL_TEMPLATES = (
    '{name} znajduje się obecnie na poziomie „Początkujący” (P). Oznacza to, że {poss} poziom alfabetyzacji ruchowej jest niższy niż typowy dla rówieśników w tym samym wieku. {name} jest na etapie rozwijania kompetencji potrzebnych do podejmowania różnorodnych aktywności fizycznych.',
    '{name} znajduje się obecnie na poziomie „Dokonujący postępów” (DP). Oznacza to, że {poss} poziom alfabetyzacji ruchowej jest zbliżony do typowego dla rówieśników w tym samym wieku. Posiada już rozwijające się kompetencje ruchowe, motywację i wiedzę, które stanowią podstawę aktywnego stylu życia.',
    '{name} znajduje się obecnie na poziomie „Sprawny” (S). Oznacza to, że {achieved} oczekiwany, dobry ogólny poziom alfabetyzacji ruchowej, wyższy niż typowy dla wielu rówieśników w tym samym wieku. {poss_cap} wynik wskazuje na poziom kompetencji sprzyjający czerpaniu korzyści zdrowotnych z aktywnego stylu życia.',
    '{name} znajduje się obecnie na poziomie „Wyróżniający się” (W). Oznacza to, że {achieved} bardzo wysoki poziom alfabetyzacji ruchowej, przewyższający wyniki większości rówieśników w tym samym wieku. Jest to najwyższa kategoria w badaniu PAPL, wskazująca na bardzo dobre podstawy do prowadzenia aktywnego i zdrowego stylu życia.',
)
STRENGTH_MEANINGS = {
    5: 'Wynik zachowań codziennych stanowi mocną stronę profilu.',
    4: 'Mocną stroną profilu są kompetencje ruchowe ocenione w badaniu.',
    6: 'Mocną stroną profilu są motywacja i pewność siebie związane z aktywnością ruchową.',
    7: 'Mocną stroną profilu są wiedza i zrozumienie zagadnień związanych z ruchem.',
}
SUPPORT_MEANINGS = {
    5: 'Większego wsparcia wymagają zachowania codzienne związane z aktywnością fizyczną.',
    4: 'Większego wsparcia wymaga rozwój kompetencji ruchowych.',
    6: 'Większego wsparcia wymagają motywacja i pewność siebie związane z aktywnością ruchową.',
    7: 'Większego wsparcia wymagają wiedza i zrozumienie zagadnień związanych z ruchem.',
}


def child_feedback(records, norms, keys, fmt, use_ai=False):
    """Use fixed third-person templates; retain signature for single and ZIP callers.

    AI is deliberately not used, even when a legacy caller passes use_ai=True.
    """
    recent=max(records,key=lambda row:row['turn'])
    name=str(recent.get('given_name') or recent.get('name','').split(' ')[0]).strip() or 'Dziecko'
    sex=recent.get('sex')
    female=sex==2
    level=recent['levels'][8] if recent['scores'][8] is not None else None
    if level is None:
        overall=(f'{name} ma w raporcie wyniki poszczególnych obszarów, ale dostępne dane '
                 'nie pozwalają przypisać kategorii ogólnej. Opis dotyczy wyłącznie ocenionych obszarów.')
        ending=('Podróż z alfabetem ruchowym trwa przez całe życie. Nowe doświadczenia i radość '
                'z ruchu mogą wspierać Twoje zdrowie, dobre samopoczucie i dalszy rozwój.')
    else:
        overall=GENERAL_TEMPLATES[level].format(name=name,poss='jej' if female else 'jego',
                    poss_cap='Jej' if female else 'Jego',achieved='osiągnęła' if female else 'osiągnął')
        ending=CHILD_ENDINGS[min(level,2)]
    available=[(idx,title,recent['levels'][idx]) for idx,title in PROFILE_DOMAINS
               if recent['scores'][idx] is not None and recent['levels'][idx] is not None]
    strengths=sorted((item for item in available if item[2]>=2),key=lambda item:-item[2])
    needs=sorted((item for item in available if item[2]<2),key=lambda item:item[2])
    parts=[]
    if not available:
        parts.append('Dostępne wyniki i normy nie pozwalają wskazać mocnych i słabszych stron profilu. Brak wyniku nie oznacza słabszych umiejętności.')
    elif not needs:
        parts.append('Wszystkie ocenione obszary mieszczą się w kategoriach „Sprawny” lub „Wyróżniający się” i stanowią mocne strony profilu. Nie wskazujemy obszaru wymagającego szczególnego wsparcia na podstawie tych kategorii.')
    elif not strengths:
        parts.append('Wszystkie ocenione obszary mieszczą się w kategoriach „Początkujący” lub „Dokonujący postępów” i wymagają dalszego wsparcia. Na podstawie tego profilu nie wyodrębniamy mocnej strony.')
        if len({value for _,_,value in available})>1:
            better=', '.join(title for _,title,value in available if value==1)
            parts.append(f'Obszary o relatywnie wyższej kategorii to: {better}.')
    else:
        # Use every relevant domain so ties never imply unmentioned needs do not exist.
        if len(strengths)==1:
            parts.append(STRENGTH_MEANINGS[strengths[0][0]])
        else:
            parts.append('Mocne strony profilu obejmują: ' + ', '.join(title for _,title,_ in strengths) + '.')
        if len(needs)==1:
            parts.append(SUPPORT_MEANINGS[needs[0][0]])
        else:
            parts.append('Większego wsparcia wymagają następujące obszary: ' + ', '.join(title for _,title,_ in needs) + '.')
        parts.append('Różnice te pomagają rozpoznać zasoby i potrzeby rozwojowe dziecka; nie określają jego możliwości na przyszłość.')
    if available and len(available)<4:
        parts.append('Opis obejmuje tylko obszary z dostępnym wynikiem i właściwą normą.')
    return [('Ogólny wynik alfabetyzacji ruchowej',overall),
            ('Mocne strony i obszary do wsparcia',' '.join(parts))],ending,PARENT_TEXT.format(name=name)
