# Research outputs for CAPL-2. capl scoring is never altered here.
codebook <- function(fields) {
  kind <- function(x) {
    if(x %in% c("age","gender")) return("Dane demograficzne")
    if(grepl("^pacer|^plank|^camsa",x)) return("Kompetencje fizyczne")
    if(grepl("^(steps[1-7]|time_on[1-7]|time_off[1-7]|non_wear_time[1-7]|self_report_pa)$",x)) return("Zachowania codzienne")
    if(grepl("^(csappa|why_active|feelings_about_pa)",x)) return("Motywacja i pewność siebie")
    return("Wiedza i zrozumienie")
  }
  description <- function(x) {
    if(x=="age") return("Wiek dziecka, w latach (CAPL-2: 8–12)")
    if(x=="gender") return("Płeć: Girl/Boy; pakiet akceptuje także warianty literowe i słowne")
    if(x=="pacer_lap_distance") return("Długość odcinka PACER w metrach (15 lub 20)")
    if(x=="pacer_laps") return("Liczba pokonanych odcinków PACER")
    if(x=="plank_time") return("Czas utrzymania pozycji plank, w sekundach")
    if(grepl("^camsa_skill_score",x)) return("CAMSA: ocena umiejętności w próbie wskazanej numerem")
    if(grepl("^camsa_time",x)) return("CAMSA: czas próby w sekundach")
    if(grepl("^steps[1-7]$",x)) return("Kroki z krokomierza w dniu wskazanym numerem")
    if(grepl("^time_on[1-7]$",x)) return("Godzina założenia krokomierza – dzień wskazany numerem")
    if(grepl("^time_off[1-7]$",x)) return("Godzina zdjęcia krokomierza – dzień wskazany numerem")
    if(grepl("^non_wear_time[1-7]$",x)) return("Czas nienoszenia krokomierza – dzień wskazany numerem")
    if(x=="self_report_pa") return("Deklarowana liczba dni z co najmniej 60 minutami MVPA w ostatnim tygodniu")
    if(grepl("^csappa",x)) return("Pozycja kwestionariusza CSAPPA – kod odpowiedzi zgodny z protokołem")
    if(grepl("^why_active",x)) return("Pozycja motywacji – kod odpowiedzi zgodny z protokołem")
    if(grepl("^feelings_about_pa",x)) return("Pozycja postrzeganej kompetencji – kod odpowiedzi zgodny z protokołem")
    return("Pozycja kwestionariusza wiedzy CAPL-2 – kod odpowiedzi zgodny z protokołem")
  }
  data.frame(Zmienna=fields,
    Obszar=vapply(fields,kind,character(1)),
    Opis=vapply(fields,description,character(1)),
    Kodowanie=vapply(fields,function(x) {
      if(x=="age") "8–12 lat" else if(x=="gender") "Boy/Girl oraz warianty akceptowane przez capl" else
      if(x=="pacer_lap_distance") "15 lub 20 m" else
      if(x=="self_report_pa") "0–7 dni" else
      if(grepl("^time_on|^time_off",x)) "Zapis godziny według formatu pakietu" else
      "Zgodnie z formularzem i instrukcją oryginalnego CAPL-2; brak danych = pusta komórka"
    },character(1)),
    Zrodlo="Barnes i Guerrero (2021), tabela 1, sekcja 2.3; podręcznik CAPL-2",
    stringsAsFactors=FALSE,check.names=FALSE)
}
# Verified coding for all 60 source columns. Preserve the original names/order.
base_codebook <- codebook
codebook <- function(fields) {
  d <- base_codebook(fields)
  d$Dopuszczalne_wartosci <- ""
  d$Znaczenie_kodow <- ""
  d$Uwagi <- "Wprowadź odpowiedź surową (nie punktację obliczoną). Braki: pusta komórka."
  for(i in seq_along(fields)) {
    x<-fields[[i]]
    allowed <- if(x=="age") "8–12; wiek w pełnych latach" else
      if(x=="gender") "Girl/Boy; g/b; Female/Male; f/m; również 1/0" else
      if(x=="pacer_lap_distance") "15 lub 20" else
      if(x=="pacer_laps") "Liczba całkowita ≥ 0; ważność sprawdza capl" else
      if(x=="plank_time") "Czas w sekundach ≥ 0" else
      if(grepl("^camsa_skill_score[12]$",x)) "Punkty za umiejętności CAMSA wg protokołu (0–14)" else
      if(grepl("^camsa_time[12]$",x)) "Czas próby CAMSA w sekundach" else
      if(grepl("^steps[1-7]$",x)) "Liczba kroków w danym dniu ≥ 0" else
      if(grepl("^time_on[1-7]$|^time_off[1-7]$",x)) "Tekst HH:MM lub format 12 h, np. 07:30, 7:30am" else
      if(grepl("^non_wear_time[1-7]$",x)) "Liczba minut nienoszenia ≥ 0" else
      if(x=="self_report_pa") "0–7 dni" else
      if(grepl("^csappa[1-6]$",x)) "1, 2, 3, 4" else
      if(grepl("^why_active[1-3]$|^feelings_about_pa[1-3]$",x)) "1, 2, 3, 4, 5" else
      if(x %in% c("pa_guideline","crf_means","ms_means","sports_skill")) "1, 2, 3, 4" else
      if(x %in% c("pa_is","pa_is_also","improve","increase","when_cooling_down","heart_rate")) "1–10" else "Sprawdź protokół"
    meaning <- if(grepl("^csappa[1-6]$",x))
      "1 = REALLY TRUE / some kids; 2 = SORT OF TRUE / some kids; 3 = REALLY TRUE / other kids; 4 = SORT OF TRUE / other kids"
      else if(grepl("^why_active[1-3]$|^feelings_about_pa[1-3]$",x))
      "Kod kolejnej opcji odpowiedzi na pięciostopniowej skali. 1–5 to kody wejściowe, nie wynik końcowy."
      else if(x %in% c("pa_guideline","crf_means","ms_means","sports_skill"))
      "Numer odpowiedzi 1–4 według oryginalnego formularza. Prawidłowość ocenia capl."
      else if(x %in% c("pa_is","pa_is_also","improve","increase","when_cooling_down","heart_rate"))
      "Numer odpowiedzi 1–10 z listy słów w zadaniu z lukami (historyjka Sally)."
      else if(x=="self_report_pa")
      "Liczba dni w ostatnich 7 dniach, w których osiągnięto co najmniej 60 minut MVPA."
      else if(x=="gender") "1 / f / g / Female / Girl = dziewczynka; 0 / m / b / Male / Boy = chłopiec."
      else if(grepl("^time_on[1-7]$",x)) "Godzina założenia krokomierza w danym dniu."
      else if(grepl("^time_off[1-7]$",x)) "Godzina zdjęcia krokomierza w danym dniu."
      else if(grepl("^non_wear_time[1-7]$",x)) "Minuty przerw w noszeniu krokomierza w ciągu dnia."
      else if(grepl("^steps[1-7]$",x)) "Dzienna liczba kroków; o ważności dnia decyduje pakiet."
      else if(x=="pacer_lap_distance") "Długość odcinka w metrach. Liczba odcinków w kolumnie pacer_laps."
      else "Zmienna ilościowa / wynik surowy; szczegóły w oryginalnym podręczniku."
    d$Dopuszczalne_wartosci[[i]]<-allowed
    d$Znaczenie_kodow[[i]]<-meaning
    if(x %in% c("pa_guideline","crf_means","ms_means","sports_skill","pa_is","pa_is_also","improve","increase","when_cooling_down","heart_rate"))
      d$Uwagi[[i]]<-"Znaczenie każdej opcji należy odczytać z wersji formularza CAPL-2 użytej w badaniu; numer nie oznacza poprawności."
    if(grepl("^csappa[1-6]$",x))
      d$Uwagi[[i]]<-if(x %in% c("csappa1","csappa3","csappa5")) "Pozycja predylekcji (predilection_score)." else "Pozycja adekwatności (adequacy_score)."
  }
  d
}

score_interpretation <- function(key) {
  if(key %in% c("capl_score","pc_score","db_score","mc_score","ku_score"))
    return(sub("_score$","_interpretation",key))
  if(key=="step_score")return("step_interpretation")
  sub("_score$","_interpretation",key)
}
numeric_summary <- function(x) {
  x<-suppressWarnings(as.numeric(x))
  ok<-x[is.finite(x)]
  c(N=sum(is.finite(x)),Braki=sum(!is.finite(x)),
    Srednia=if(length(ok)) mean(ok) else NA_real_,
    SD=if(length(ok)>1) sd(ok) else NA_real_,
    Mediana=if(length(ok)) median(ok) else NA_real_,
    Q1=if(length(ok)) unname(quantile(ok,.25)) else NA_real_,
    Q3=if(length(ok)) unname(quantile(ok,.75)) else NA_real_,
    Minimum=if(length(ok)) min(ok) else NA_real_,
    Maksimum=if(length(ok)) max(ok) else NA_real_)
}
research_tables <- function(d, score="capl_score") {
  if(!score %in% names(d))score<-"capl_score"
  category <- score_interpretation(score)
  age <- suppressWarnings(as.numeric(d$age))
  sex <- tolower(as.character(capl::validate_gender(d$gender)))
  sex[is.na(sex)] <- "Brak"
  catval <- if(category %in% names(d)) as.character(d[[category]]) else rep(NA_character_,nrow(d))
  catval[is.na(catval)] <- "Brak interpretacji"
  base <- data.frame(Wiek=age,Plec=sex,Kategoria=catval,Wynik=suppressWarnings(as.numeric(d[[score]])))
  counts <- function(columns) {
    t <- as.data.frame(table(base[columns],useNA="ifany"),stringsAsFactors=FALSE)
    names(t)[ncol(t)] <- "N"
    # Percent within each demographic stratum, excluding invalid interpretations from denominators.
    groups <- if(length(columns)>1) columns[-length(columns)] else character()
    if(length(groups)){
      den<-aggregate(t$N,by=t[groups],FUN=sum)
      names(den)[ncol(den)]<-"denominator"
      t<-merge(t,den,by=groups,sort=FALSE)
      t$Procent<-ifelse(t$denominator>0,round(100*t$N/t$denominator,1),NA_real_)
    } else t$Procent<-round(100*t$N/sum(t$N),1)
    t
  }
  domains <- c("pc_score","db_score","mc_score","ku_score")
  maxs <- c(30,30,30,10)
  dom <- data.frame(Domena=domains,
    N=vapply(domains,function(k)sum(!is.na(d[[k]])),integer(1)),
    Srednia=vapply(domains,function(k)if(all(is.na(d[[k]]))) NA_real_ else mean(d[[k]],na.rm=TRUE),numeric(1)),
    Maksimum=maxs)
  dom$Procent_maksimum<-round(100*dom$Srednia/dom$Maksimum,1)
  stcols <- intersect(c("pc_status","db_status","mc_status","ku_status","capl_status"),names(d))
  st <- do.call(rbind,lapply(stcols,function(k) {
    z <- as.data.frame(table(ifelse(is.na(d[[k]]),"Brak statusu",as.character(d[[k]]))))
    data.frame(Domena=k,Status=as.character(z$Var1),N=z$Freq)
  }))
  miss <- data.frame(Zmienna=names(d),
    N_brak=vapply(d,function(x)sum(is.na(x)),integer(1)))
  miss$Procent_brak<-round(100*miss$N_brak/nrow(d),1)
  overall <- data.frame(Wskaznik=score,t(numeric_summary(base$Wynik)),check.names=FALSE)
  by_group <- do.call(rbind,lapply(split(seq_len(nrow(base)),
    interaction(base$Wiek,base$Plec,drop=TRUE,lex.order=TRUE)),function(ix){
    data.frame(Wiek=base$Wiek[ix[1]],Plec=base$Plec[ix[1]],
      Wskaznik=score,t(numeric_summary(base$Wynik[ix])),
      check.names=FALSE)
  }))
  list("Opis ogolem"=overall,"Opis wiek plec"=by_group,
     "Profil domen"=dom,"Kategorie"=counts("Kategoria"),
    "Kategorie wg plci"=counts(c("Plec","Kategoria")),
    "Kategorie wg wieku"=counts(c("Wiek","Kategoria")),
    "Status domen"=st,"Braki"=miss)
}

# Statistical tables across all available numerical CAPL-2 outputs;
# original scores and interpretations remain available in the raw results sheet.
all_numeric_summaries <- function(d) {
  keys <- names(d)[vapply(d,is.numeric,logical(1))]
  keys <- keys[!(keys %in% c("age")) & !grepl("^steps[1-7]$|^non_wear_time[1-7]$",keys)]
  all <- do.call(rbind,lapply(keys,function(key) {
    data.frame(Wskaznik=key,t(numeric_summary(d[[key]])),check.names=FALSE)
  }))
  rownames(all)<-NULL
  all
}
