# Publikacja PAPL Calculator na shinyapps.io

Aplikacja **nie działa na GitHub Pages**; wymaga serwera R.

## Uruchomienie w Visual Studio Code
1. Zainstaluj R.
2. Otwórz katalog projektu.
3. Uruchom R i wpisz:
```r
install.packages(c("shiny","capl","readxl","writexl","ggplot2","DT","rsconnect"))
shiny::runApp(".")
```
4. W zakładce Import Excel pobierz szablon i przetestuj import.

## Publikacja po lokalnych testach
1. Utwórz konto w https://www.shinyapps.io/
2. W panelu shinyapps.io otwórz **Account → Tokens** i skopiuj token oraz secret. **Nie umieszczaj tych danych na GitHubie.**
3. Skonfiguruj połączenie w lokalnej konsoli R zgodnie z instrukcją na stronie shinyapps.io:
```r
rsconnect::setAccountInfo(name="TWOJA_NAZWA", token="TWÓJ_TOKEN", secret="TWÓJ_SECRET")
rsconnect::deployApp(appDir=".", appName="papl-calculator")
```
4. Otwórz adres wskazany przez shinyapps.io i zweryfikuj działanie na danych syntetycznych.

## Uwaga
- Bez wdrożenia w shinyapps.io repozytorium GitHub zawiera **kod**, a nie działającą publiczną stronę.
- Aplikacja w Shiny przetwarza przesłane pliki na serwerze aplikacji. Nie przesyłaj danych osobowych uczniów przed ustaleniem zgodności z wymogami ochrony danych.
- Kod to prototyp, wymagający testów na zweryfikowanych danych referencyjnych przed udostępnieniem do badań.
