# PAPL Calculator (prototyp)

Aplikacja R Shiny wykorzystująca oryginalny pakiet [capl](https://cran.r-project.org/package=capl) do obliczania CAPL-2 oraz polskie zakresy referencyjne PAPL (8–12 lat).

**Status:** wersja testowa, nie do zastosowania klinicznego ani do oceniania dzieci przed walidacją progów i kompletności protokołu.

## Uruchomienie lokalne

1. Zainstaluj R.
2. W konsoli R uruchom:
```r
install.packages(c("shiny", "capl", "readxl", "writexl", "ggplot2", "DT"))
shiny::runApp(".")
```

## Funkcje
- Dane pojedynczego dziecka (formularz wyników surowych i opcjonalnie wyników domenowych)
- Import Excel/CSV dla grup
- Oryginalne obliczenia `capl::get_capl()`, jeśli dane surowe umożliwiają ich wyliczenie
- Klasyfikacje PAPL i kanadyjskie klasyfikacje wyliczone przez `capl`
- Eksport zestawienia do Excel oraz wykresy

## Ograniczenia
- Wyniki PAPL są interpretowane w oparciu o dostarczone polskie tabele referencyjne. Wersja 1 nie zmienia algorytmów punktacji CAPL-2.
- Polskie progi z miejscami dziesiętnymi są stosowane z uwzględnieniem dokładności prezentacji w tabelach; przypadki graniczne należy zweryfikować.
- Wyniki częściowe pozostają `NA`, jeśli brak danych potrzebnych do wyliczenia.
- Nie wgrywaj danych identyfikujących dzieci na publicznie hostowaną aplikację przed oceną ochrony danych.

Źródło norm PAPL: raport *Aktywny dzisiaj dla zdrowia w przyszłości*, tabele 56–62, s. 130–134.

## Wdrożenie
Źródło aplikacji na GitHubie, uruchomienie poprzez shinyapps.io (nie GitHub Pages). Publikację przeprowadź po lokalnych testach, przez `rsconnect`.
