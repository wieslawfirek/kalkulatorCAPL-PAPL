# RAPORTY PAPL

Generator raportów CAPL-2 według poprawionych polskich norm PAPL (tabele 56–62).
Import Excela, raport indywidualny z pełną historią, raport klasowy, paczka PDF dla klasy
oraz raport szkolny z podziałem na klasy. Excel pozostaje w pamięci karty przeglądarki
i jest przesyłany na czas pojedynczego żądania. Serwer nie zapisuje skoroszytu.
Repozytorium zawiera kod i normy.

Lokalna weryfikacja: `python -m pip install -r requirements.txt`, następnie `python app.py`.
Aplikacja jest dostępna pod http://127.0.0.1:8765.

Vercel: katalog projektu `raporty-papl`, framework Other, wykrywanie funkcji Python.
Ustaw zmienną `PAPL_PASSWORD` na hasło dostępu. Nazwa użytkownika to `papl`.
Bez tej zmiennej aplikacja na Vercelu zwraca 503. Dane uczniów należy przetwarzać dopiero
w środowisku dopuszczonym do tego celu.
