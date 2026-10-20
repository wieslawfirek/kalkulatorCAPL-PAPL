# CAPL-2 research workflow; the original CAPL calculation is never overwritten.
library(shiny)
library(capl)
library(readxl)
library(writexl)
library(ggplot2)
library(DT)
source("R/reporting.R", local=TRUE)

norms <- read.csv("data/papl_norms.csv",stringsAsFactors=FALSE)
original_fields <- names(capl::get_capl_demo_data(n=1))
levels_pl <- c("Początkujący","Dokonujący postępów","Sprawny","Wyróżniający się")
# Reference-table columns are transcribed from the supplied PAPL report.
# Interpretation is an ADD-ON, not part of the authors' capl R package.
papl_class <- function(age, gender, score, key) {
  if (length(score)!=1 || is.na(score) || !is.finite(score) || is.na(age) || is.na(gender))
    return(NA_character_)
  g <- tolower(trimws(as.character(gender)))
  sex <- if(g %in% c("girl","female","f","g","dziewczynka","k","1")) "Girl" else
    if(g %in% c("boy","male","m","b","chłopiec","chlopiec","0")) "Boy" else NA_character_
  if(is.na(sex)) return(NA_character_)
  ref <- norms[norms$sex==sex & norms$age==as.numeric(age) & norms$metric==key,,drop=FALSE]
  if(nrow(ref)!=1) return(NA_character_)
  # Thresholds are supplied to the precision displayed in the reference tables.
  integer_metric <- key %in% c("pacer_20m_laps","camsa_skill_time_score","step_average","self_report_pa")
  v <- round(as.numeric(score), if(integer_metric) 0 else 1)
  if(v < ref$begin_max) levels_pl[1] else if(v <= ref$progress_max) levels_pl[2] else
    if(v <= ref$achieve_max) levels_pl[3] else levels_pl[4]
}
papl_map <- c(capl_score="capl_score",pc_score="pc_score",db_score="db_score",
 mc_score="mc_score",ku_score="ku_score",pacer_20m_laps="pacer_laps_20m",
 plank_time="plank_time",camsa_skill_time_score="camsa_skill_time_score2",
 step_average="step_average",self_report_pa="self_report_pa")
# Some reference variables require special handling, e.g. CAMSA score before
# conversion to the domain score. Only use values when demonstrably equivalent.
papl_map <- papl_map[names(papl_map)!="camsa_skill_time_score"]

run_capl <- function(raw,with_papl=TRUE) {
  if(!is.data.frame(raw) || !nrow(raw)) stop("Prześlij niepustą tabelę.")
  if(anyDuplicated(names(raw))) stop("Występują zduplikowane nazwy kolumn.")
  if(!all(c("age","gender") %in% names(raw)))
    stop("Brak kolumn age lub gender – zobacz szablon CAPL-2.")
  # Delegate all scoring, validation, missing values and weighting to original package.
  # Deterministic seed only shields CAPL's stochastic handling of rare missing cases.
  had_seed <- exists(".Random.seed",envir=.GlobalEnv,inherits=FALSE)
  if(had_seed) old_seed <- get(".Random.seed",envir=.GlobalEnv)
  on.exit({
    if(had_seed) assign(".Random.seed",old_seed,envir=.GlobalEnv)
    else if(exists(".Random.seed",envir=.GlobalEnv,inherits=FALSE))
      rm(".Random.seed",envir=.GlobalEnv)
  },add=TRUE)
  set.seed(20261018L)
  result <- capl::get_capl(raw_data=raw,sort="asis")
  if(with_papl) {
    for(key in names(papl_map)) {
      source <- unname(papl_map[[key]])
      if(!(source %in% names(result))) next
      result[[paste0("PAPL_",key)]] <- vapply(seq_len(nrow(result)),function(i)
        papl_class(result$age[i],result$gender[i],
          suppressWarnings(as.numeric(result[[source]][i])),key),character(1))
    }
  }
  result
}
# Original 40 derived output columns as listed in Barnes & Guerrero (2021), pp. 15–16.
capl_derived <- c(
 "pacer_laps_20m","pacer_score","pacer_interpretation","plank_score",
 "plank_interpretation","camsa_time_score1","camsa_time_score2",
 "camsa_skill_time_score1","camsa_skill_time_score2","camsa_score",
 "camsa_interpretation","pc_score","pc_interpretation","pc_status",
 "step_average","valid_days","step_score","step_interpretation",
 "self_report_pa_score","db_score","db_interpretation","db_status",
 "predilection_score","adequacy_score","intrinsic_motivation_score",
 "pa_competence_score","mc_score","mc_interpretation","mc_status",
 "pa_guideline_score","crf_means_score","ms_means_score",
 "sports_skill_score","fill_in_the_blanks_score",
 "ku_score","ku_interpretation","ku_status",
 "capl_score","capl_interpretation","capl_status")
metrics <- c("Wynik ogólny"="capl_score","Kompetencje fizyczne"="pc_score",
 "Zachowania codzienne"="db_score","Motywacja i pewność siebie"="mc_score",
 "Wiedza i zrozumienie"="ku_score","PACER"="pacer_score",
 "Deska"="plank_score","CAMSA"="camsa_score","Kroki"="step_score")

ui <- fluidPage(
 tags$head(tags$style(HTML("
   body {background:#f5f8fb;color:#19344d;}
   .container-fluid{max-width:1350px}
   h2,h3{color:#17456b}
   .well{background:white;border-radius:12px}
 "))),
 titlePanel("CAPL-2 | Obliczenia i interpretacja wyników"),
 p("Oryginalny pakiet R capl (Barnes i Guerrero, 2021). Polskie normy PAPL są opcjonalnym rozszerzeniem."),
 tabsetPanel(
  tabPanel("1. Import danych",br(),
    fluidRow(
      column(5,wellPanel(
        h4("Prześlij dane surowe CAPL-2"),
        fileInput("file","Plik Excel / CSV",accept=c(".xlsx",".xls",".csv")),
        checkboxInput("apply_papl","Dodaj polskie klasyfikacje PAPL",TRUE),
        actionButton("calculate","Oblicz wszystkie wyniki (get_capl)",class="btn-primary"),
        hr(),
        downloadButton("template","Pobierz szablon z książką kodów"),
        br(),br(),
        downloadButton("demo","Pobierz syntetyczne dane przykładowe"),
        p(class="text-muted","Jeden wiersz to jedno dziecko. Zachowaj oryginalne nazwy 60 kolumn. Bez imion, nazwisk i identyfikatorów osobowych.")
      )),
      column(7,
        h4("Status analizy"),verbatimTextOutput("status"),
        h4("Kontrola wymaganych zmiennych"),tableOutput("quality"),
        p("Braki i wartości nieprawidłowe przetwarza oryginalny pakiet capl; nie uzupełniamy ich automatycznie zerami.")
      )
    )
  ),
  tabPanel("2. Wyniki CAPL-2",br(),
    p("Pełny wynik oryginalnej funkcji get_capl(): wszystkie kolumny wejściowe i wyliczone. Dodatkowe kolumny PAPL mają prefiks PAPL_."),
    radioButtons("columns","Zakres kolumn",inline=TRUE,
      choices=c("Wszystkie"="all","40 wyników pakietu"="derived",
                "Dane surowe"="raw","Polskie interpretacje"="papl")),
    DTOutput("results"),br(),
    downloadButton("export","Pobierz pełną bazę wynikową XLSX"),
    downloadButton("export_csv","Pobierz CSV")
  ),
  tabPanel("3. Jakość danych",br(),
    h4("Kompletność wyników i status domen"),
    DTOutput("quality_status"),
    h4("Kompletność oryginalnych 40 wyników"),
    DTOutput("quality_variables")
  ),
  tabPanel("4. Zestawienia liczbowe",br(),
    p("Tabele statystyczne do samodzielnej analizy i wizualizacji. Bez wykresów."),
    selectInput("summary_metric","Wskaźnik CAPL-2",choices=metrics),
    selectInput("summary_table","Zestawienie",choices=c(
      "Statystyki opisowe ogółem"="Opis ogolem",
      "Statystyki opisowe według wieku i płci"="Opis wiek plec",
      "Profil czterech domen"="Profil domen",
      "Kategorie CAPL-2"="Kategorie",
      "Kategorie według płci"="Kategorie wg plci",
      "Kategorie według wieku"="Kategorie wg wieku",
      "Statusy kompletności"="Status domen",
      "Braki danych"="Braki")),
    DTOutput("summary_results"),br(),
    downloadButton("export_analysis","Eksport pełnych wyników i zestawień do Excela")
  ),
  tabPanel("5. Normy PAPL – dodatek",br(),
    p("Opcjonalne klasyfikacje na podstawie polskich tabel normatywnych. Oryginalne wyniki i interpretacje kanadyjskie pozostają niezmienione."),
    selectInput("norm_metric","Wybierz wynik",choices=setNames(unique(norms$metric),unique(norms$metric))),
    DTOutput("norm_table"),
    p("Nie wszystkie zmienne PAPL mają odpowiednik bezpośrednio dostępny w przeliczonym CAPL-2. Nie przypisujemy kategorii przy braku porównywalnego wyniku.")
  ),
  tabPanel("Metodyka",br(),
    h4("Zakres narzędzia"),
    p("Pakiet capl: 60 pól wejściowych → 40 dodatkowych wyników, statusów i interpretacji. Silnik: capl::get_capl()."),
    p("Oryginalne 40 pól jest zachowanych wraz z pierwotnymi nazwami; CAPL-2 jest źródłem obliczeń i kanadyjskich norm."),
    p("PAPL to oddzielna warstwa interpretacyjna; nie zmienia punktowania oryginalnego pakietu."),
    p("Braki w danych i dzielenie przez dostępne komponenty podlegają regułom autorów capl."),
    p("Publiczny serwer Shiny przetwarza przesłane dane na serwerze – nie wysyłaj danych pozwalających zidentyfikować dzieci."),
    tags$a(href="https://github.com/wieslawfirek/kalkulatorCAPL-PAPL",
       "Kod źródłowy i testy na GitHubie",target="_blank"),
    p("Barnes, J. D., & Guerrero, M. D. (2021). PLOS ONE, 16(2), e0243841.")
  )
 )
)

server <- function(input,output,session) {
 raw <- eventReactive(input$calculate,{
   req(input$file)
   tryCatch({
     d <- if(grepl("\\.csv$",input$file$name,ignore.case=TRUE))
       read.csv(input$file$datapath,stringsAsFactors=FALSE,check.names=FALSE)
       else as.data.frame(readxl::read_excel(input$file$datapath))
     d
   },error=function(e){showNotification(conditionMessage(e),type="error");NULL})
 })
 results <- reactive({
   d<-raw();req(d)
   tryCatch(run_capl(d,isTRUE(isolate(input$apply_papl))),
     error=function(e){showNotification(conditionMessage(e),type="error",duration=12);NULL})
 })
 output$status <- renderText({
   d<-results();req(d)
   x<-sum(!is.na(d$capl_score))
   paste0("Przeliczono ",nrow(d)," uczestników.\n",
     "Wynik ogólny dostępny: ",x," / ",nrow(d),".\n",
     "Wyniki oryginalne: ",sum(capl_derived %in% names(d))," / 40 kolumn.\n",
     "Kolumny w tabeli wynikowej: ",ncol(d),".\n",
     "Wyniki ogólne o statusie complete: ",sum(!is.na(d$capl_status) & d$capl_status=="complete")," / ",nrow(d),".\n",
     "Uwaga: pakiet capl może obliczać wyniki także przy niekompletnych pomiarach. Sprawdź statusy domen i arkusz Kompletnosc osob.")
 })
 output$quality <- renderTable({
   d<-raw();req(d)
   data.frame(Pole=c("Liczba uczestników","Kolumny wejściowe","Wymagane kolumny CAPL-2",
       "Brakujące kolumny protokołu","Uczestnicy bez wieku","Uczestnicy bez płci"),
     Wartość=c(nrow(d),ncol(d),length(original_fields),
       paste(setdiff(original_fields,names(d)),collapse=", "),
       if("age" %in% names(d)) sum(is.na(d$age)) else nrow(d),
       if("gender" %in% names(d)) sum(is.na(d$gender)) else nrow(d)))
 })
 selected_data <- reactive({
   d<-results();req(d)
   keys<-switch(input$columns,
      derived=intersect(capl_derived,names(d)),
      raw=intersect(original_fields,names(d)),
      papl=grep("^PAPL_",names(d),value=TRUE),
      names(d))
   d[,keys,drop=FALSE]
 })
 output$results <- renderDT({
   d<-selected_data();req(d)
   DT::datatable(d,filter="top",options=list(scrollX=TRUE,pageLength=12,
     deferRender=TRUE))
 })
 output$quality_status <- renderDT({
   d<-results();req(d)
   ks<-intersect(c("pc_status","db_status","mc_status","ku_status","capl_status"),names(d))
   out<-do.call(rbind,lapply(ks,function(k) {
     tab<-table(ifelse(is.na(d[[k]]),"NA",as.character(d[[k]])))
     data.frame(domena=k,status=names(tab),liczba=as.integer(tab))
   }))
   DT::datatable(out,options=list(pageLength=20))
 })
 output$quality_variables <- renderDT({
   d<-results();req(d)
   ks<-intersect(capl_derived,names(d))
   DT::datatable(data.frame(zmienna=ks,
      wyniki_dostępne=vapply(d[ks],function(x)sum(!is.na(x)),integer(1)),
      braki=vapply(d[ks],function(x)sum(is.na(x)),integer(1))),
      options=list(pageLength=40,dom="tip"))
 })
 output$summary_results <- renderDT({
   d<-results();req(d)
   tabs<-research_tables(d,input$summary_metric)
   DT::datatable(tabs[[input$summary_table]],options=list(scrollX=TRUE,pageLength=20))
 })
 output$export_analysis <- downloadHandler(
   filename=function()paste0("CAPL2_raport_",Sys.Date(),".xlsx"),
   content=function(file) {
     d<-results();req(d)
     sheets<-c(list("Pelne wyniki"=d,
       "Ksiazka kodow"=codebook(original_fields),
       "Statystyki wynikow"=all_numeric_summaries(d),
       "Czestosci kodow"=input_frequencies(d),
       "Kompletnosc osob"=participant_completeness(d,original_fields)),research_tables(d,input$summary_metric))
     writexl::write_xlsx(sheets,file)
   })
 output$norm_table <- renderDT({
   d<-norms[norms$metric==input$norm_metric,,drop=FALSE]
   DT::datatable(d,options=list(pageLength=12))
 })
 output$template <- downloadHandler(filename=function()"CAPL2_60_kolumn_szablon.xlsx",
   content=function(file){
     d<-capl::get_capl_demo_data(n=1)[FALSE,,drop=FALSE]
     writexl::write_xlsx(list("Dane CAPL2"=d,
       "Ksiazka kodow"=codebook(original_fields)),file)
   })
 output$demo <- downloadHandler(filename=function()"CAPL2_przykladowe_syntetyczne.xlsx",
   content=function(file){
     d<-capl::get_capl_demo_data(n=20)
     writexl::write_xlsx(d,file)
   })
 output$export <- downloadHandler(filename=function()paste0("CAPL2_wyniki_",Sys.Date(),".xlsx"),
   content=function(file){
     d<-results();req(d)
     q<-data.frame(zmienna=names(d),rodzaj=ifelse(names(d)%in%original_fields,
       "Dane wejściowe",ifelse(grepl("^PAPL_",names(d)),"PAPL – dodatek","CAPL-2 – wynik")))
     writexl::write_xlsx(c(list("Wyniki"=d,"Słownik kolumn"=q,
       "Ksiazka kodow"=codebook(original_fields),
       "Statystyki wynikow"=all_numeric_summaries(d),
       "Czestosci kodow"=input_frequencies(d),
       "Kompletnosc osob"=participant_completeness(d,original_fields)),research_tables(d,"capl_score")),file)
   })
 output$export_csv <- downloadHandler(filename=function()"CAPL2_wyniki.csv",
   content=function(file){d<-results();req(d);write.csv(d,file,row.names=FALSE,na="")})
}
shinyApp(ui,server)
