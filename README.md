# CAPL-2 – pełne przeliczanie danych (R Shiny)

Aplikacja korzysta bezpośrednio z pakietu R **capl** (Barnes & Guerrero, 2021, PLOS ONE, doi:10.1371/journal.pone.0243841).

## Cel

**Dane surowe (60 pól) → capl::get_capl() → 40 oryginalnych zmiennych wynikowych.**

Nie jest to kalkulator dla pojedynczego dziecka. Zasadniczym zadaniem aplikacji jest zbiorcze przeliczanie bazy badawczej i przygotowanie wyników do dalszej analizy statystycznej.

## Funkcje

- Import XLSX/CSV (wiele uczestników), pusty szablon 60 kolumn i dane demonstracyjne.
- Oryginalne punktowanie, kategorie kanadyjskie, statusy kompletności i reguły braków pakietu `capl`.
- Pełny podgląd 40 wyliczonych zmiennych oraz 60 wejściowych.
- Kontrola kompletności wyników i brakujących pól.
- Moduł zestawień liczbowych zamiast wykresów: liczebności, odsetki, średnie, SD, mediany, kwartyle, minima/maksima i braki danych.
- Szablon XLSX zawierający arkusz 60 zmiennych wejściowych i książkę kodów. Kodowanie pozycji kwestionariuszowych wymaga sprawdzenia w oryginalnym podręczniku CAPL-2.
- Zbiorczy raport XLSX: pełne dane jednostkowe, książka kodów, statystyki wszystkich wskaźników liczbowych i zestawienia kategorii CAPL-2 według wieku i płci.
- Eksport wszystkich kolumn do XLSX/CSV.
- Opcjonalne normy polskie PAPL jako **osobna warstwa interpretacyjna** (`PAPL_...`), bez zmiany kanadyjskiego punktowania.

**Uwaga:** normy PAPL wymagają zgodności miary i punktacji. Nie wszystkie polskie miary mają bezpośredni odpowiednik zwracany przez `capl`; nie przypisujemy im kategorii automatycznie bez sprawdzenia.

## Uruchomienie lokalne

```r
install.packages(c("shiny","capl","readxl","writexl","ggplot2","DT"))
shiny::runApp(".")
```

## Audyt

GitHub Actions: **Audit CAPL-2 and PAPL scoring**. Testy porównują pełny wynik `get_capl()` z wynikiem aplikacji oraz testują granice norm PAPL. Wymagane jest uruchomienie audytu po każdej zmianie.

## Publikacja

Kod jest w GitHubie, aplikacja działa na Posit Connect Cloud. Po udanym audycie uruchom `Generate Posit manifest`, potem **Republish** w Posit Connect Cloud. Nie publikuj przed pomyślnym zakończeniem testów.

## Prywatność

Przy hostingu Shiny dane wgrywane do aplikacji są przetwarzane na serwerze. Nie przesyłaj danych pozwalających zidentyfikować dzieci bez właściwych zabezpieczeń i podstawy prawnej.

## Źródła

Barnes, J. D., & Guerrero, M. D. (2021). *An R Package for Computing Canadian Assessment of Physical Literacy (CAPL) scores and interpretations from raw data*. PLOS ONE, 16(2), e0243841.

Normy PAPL: przekazany polski raport z tabelami referencyjnymi.
