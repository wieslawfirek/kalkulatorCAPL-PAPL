library(shiny)
library(capl)
library(readxl)
library(writexl)
library(ggplot2)
library(DT)

norms <- read.csv("data/papl_norms.csv", stringsAsFactors = FALSE)
metric_labels <- c(capl_score="Wynik ogólny", pc_score="Kompetencje fizyczne",
  db_score="Zachowania codzienne", mc_score="Motywacja i pewność siebie",
  ku_score="Wiedza i zrozumienie", pacer_20m_laps="BEEP-TEST (20 m)",
  plank_time="DESKA (sekundy)", camsa_skill_time_score="CAMSA (0–28)",
  step_average="Średnia liczba kroków", self_report_pa="Dni MVPA")
metric_names <- names(metric_labels)
levels_pl <- c("Początkujący","Dokonujący postępów","Sprawny","Wyróżniający się")
protocol_map <- c(capl_score="capl",pc_score="pc",db_score="db",
 mc_score="mc",ku_score="ku",pacer_20m_laps="pacer",
 plank_time="plank",camsa_skill_time_score="camsa",
 step_average="steps",self_report_pa="self_report_pa")

# Granice z raportu mają różną precyzję. Wyniki zaokrąglamy do:
# 1 miejsca dla wyników punktowych i deski, 0 dla liczby kroków, odcinków, CAMSA i dni MVPA.
papl_round <- function(x, key) {
  if (key %in% c("pacer_20m_laps","camsa_skill_time_score","step_average","self_report_pa")) round(x)
  else round(x, 1)
}
papl_class <- function(age, gender, score, key) {
  if (length(score) != 1 || is.na(score) || !is.finite(score) ||
      is.na(age) || is.na(gender) || !(key %in% norms$metric)) return(NA_character_)
  g <- if (tolower(trimws(as.character(gender))) %in% c("girl","female","f","g","dziewczynka","k")) "Girl" else
       if (tolower(trimws(as.character(gender))) %in% c("boy","male","m","b","chłopiec","chlopiec")) "Boy" else NA_character_
  if (is.na(g)) return(NA_character_)
  n <- norms[norms$sex == g & norms$age == as.numeric(age) & norms$metric == key,]
  if (nrow(n) != 1) return(NA_character_)
  v <- papl_round(as.numeric(score),key)
  # First interval: < lower threshold; next: up to progress_max;
  # next: up to achieve_max; fourth: higher.
  if (v < n$begin_max) return(levels_pl[1])
  if (v <= n$progress_max) return(levels_pl[2])
  if (v <= n$achieve_max) return(levels_pl[3])
  levels_pl[4]
}
as_number <- function(v) {
  if (is.null(v) || length(v)==0 || all(is.na(v))) return(NA_real_)
  suppressWarnings(as.numeric(gsub(",", ".", as.character(v[1]), fixed=TRUE)))
}
get_metric <- function(d,key) {
  if (key %in% names(d)) as_number(d[[key]]) else NA_real_
}
value_or_na <- function(x) if (is.null(x) || length(x)==0 || is.na(x)) NA_real_ else as.numeric(x)
one_row <- function(input) {
  d <- as.data.frame(as.list(setNames(rep(NA_real_, 9),
    c("pacer_lap_distance","pacer_laps","plank_time","camsa_skill_score1",
      "camsa_time1","camsa_skill_score2","camsa_time2","self_report_pa","age"))))
  d$age <- as.integer(input$age)
  d$gender <- input$gender
  for (key in intersect(names(d),c("pacer_laps","plank_time","camsa_skill_score1",
    "camsa_time1","camsa_skill_score2","camsa_time2")))
    d[[key]] <- value_or_na(input[[key]])
  d$pacer_lap_distance <- 20
  d$self_report_pa <- value_or_na(input$self_report_pa)
  d
}
process_data <- function(raw, supplied=NULL) {
  if (!all(c("age","gender") %in% names(raw)))
    stop("Brak wymaganych kolumn age oraz gender.", call.=FALSE)
  if (!nrow(raw)) stop("Plik nie zawiera danych.", call.=FALSE)
  raw$age <- suppressWarnings(as.numeric(raw$age))
  if (any(!is.na(raw$age) & !(raw$age %in% 8:12)))
    stop("Normy są dostępne wyłącznie dla wieku 8–12 lat.",call.=FALSE)
  raw$gender <- as.character(raw$gender)
  # Nie można bezpiecznie użyć zgadywanych wartości ani zastępować braków zerami.
  res <- capl::get_capl(as.data.frame(raw))
  if (!is.null(supplied)) {
    for (k in names(supplied)) if (!is.na(supplied[[k]])) res[[k]] <- supplied[[k]]
    # Wynik z podanych domen wyliczamy oryginalną funkcją pakietu.
    if (all(vapply(c("pc_score","db_score","mc_score","ku_score"),
        function(k) k %in% names(res) && !is.na(res[[k]][1]), logical(1))))
      res$capl_score <- capl::get_capl_score(res$pc_score,res$db_score,res$mc_score,res$ku_score)
  }
  for (k in metric_names) {
    if (!(k %in% names(res))) res[[k]] <- NA_real_
  }
  # Wynik surowy CAMSA: maksimum z obu prób (punktacja umiejętności + czasu).
  if ("camsa_skill_time_score" %in% names(raw)) {
    res$camsa_skill_time_score <- suppressWarnings(as.numeric(raw$camsa_skill_time_score))
  } else if (all(c("camsa_skill_time_score1","camsa_skill_time_score2") %in% names(res))) {
    x <- suppressWarnings(as.numeric(res$camsa_skill_time_score1))
    y <- suppressWarnings(as.numeric(res$camsa_skill_time_score2))
    res$camsa_skill_time_score <- ifelse(is.na(x)&is.na(y),NA_real_,pmax(x,y,na.rm=TRUE))
  }
  # Możliwość podania średniej liczby kroków jako wyniku gotowego (bez liczenia punktów domeny).
  if ("step_average" %in% names(raw)) res$step_average <- suppressWarnings(as.numeric(raw$step_average))
  for (k in metric_names) {
    res[[paste0("PAPL_", k)]] <- vapply(seq_len(nrow(res)),function(i)
      papl_class(res$age[i],res$gender[i],get_metric(res[i,,drop=FALSE],k),k),
      character(1))
    # Oryginalne kanadyjskie normy liczone funkcją capl, także przy wyniku
    # domenowym dostarczonym ręcznie (bez dopisywania fikcyjnych wyników surowych).
    res[[paste0("CAPL_", k)]] <- tryCatch(
      as.character(capl::get_capl_interpretation(
        age=res$age,gender=res$gender,score=as.numeric(res[[k]]),protocol=protocol_map[[k]])),
      error=function(e) rep(NA_character_,nrow(res)))
  }
  res
}

ui <- fluidPage(
  tags$head(tags$style(HTML("
    body {background:#f5f8fb;color:#19344d;}
    .container-fluid {max-width:1200px;}
    .well {background:white;border:1px solid #dce5ef;border-radius:12px;}
    h2,h3 {color:#17456b;}
    .nav-tabs>li.active>a {font-weight:600;}
    .small-note {color:#526a7d;font-size:12px;}
  "))),
  titlePanel("PAPL Calculator | CAPL-2 & PAPL"),
  p("Obliczenia oryginalnym pakietem R capl oraz niezależna interpretacja według polskich norm PAPL."),
  tabsetPanel(
    tabPanel("Jedno dziecko",
      sidebarLayout(
        sidebarPanel(
          h4("Dane dziecka"),
          selectInput("gender","Płeć",c("Dziewczynka"="Girl","Chłopiec"="Boy")),
          selectInput("age","Wiek",choices=8:12,selected=10),
          h4("Wyniki surowe (opcjonalne)"),
          numericInput("pacer_laps","BEEP-TEST – odcinki 20 m",NA,min=0),
          numericInput("plank_time","DESKA – sekundy",NA,min=0),
          numericInput("camsa_skill_score1","CAMSA próba 1 – punkty za umiejętności",NA,min=0,max=14),
          numericInput("camsa_time1","CAMSA próba 1 – czas w sekundach",NA,min=0),
          numericInput("camsa_skill_score2","CAMSA próba 2 – punkty za umiejętności",NA,min=0,max=14),
          numericInput("camsa_time2","CAMSA próba 2 – czas w sekundach",NA,min=0),
          numericInput("self_report_pa","Dni MVPA (0–7)",NA,min=0,max=7),
          h4("Gotowe wyniki domen (opcjonalne)"),
          p(class="small-note","Wpisuj tylko wyniki wcześniej poprawnie obliczone. Braki nie oznaczają zera."),
          numericInput("pc_score","Kompetencje fizyczne (0–30)",NA,min=0,max=30),
          numericInput("db_score","Zachowania codzienne (0–30)",NA,min=0,max=30),
          numericInput("mc_score","Motywacja i pewność siebie (0–30)",NA,min=0,max=30),
          numericInput("ku_score","Wiedza i zrozumienie (0–10)",NA,min=0,max=10),
          actionButton("calculate_one","Oblicz",class="btn-primary")
        ),
        mainPanel(h3("Wyniki i interpretacja"),p("Niewyliczalne wyniki pozostają puste."),
          DTOutput("individual_table"),downloadButton("save_individual","Pobierz wyniki XLSX"),
          hr(),plotOutput("individual_plot",height="350px"))
      )
    ),
    tabPanel("Import Excel",
      br(),fileInput("excel","Wybierz plik XLSX lub CSV",accept=c(".xlsx",".xls",".csv")),
      p(class="small-note","Wymagane: age, gender. Pozostałe kolumny muszą używać nazw z pakietu capl. Opcjonalnie: gotowe wyniki domen oraz step_average."),
      actionButton("calculate_group","Oblicz grupę",class="btn-primary"),
      downloadButton("template","Pobierz oficjalny szablon danych"),
      hr(),verbatimTextOutput("import_status"),
      DTOutput("group_table"),downloadButton("save_group","Pobierz wyniki XLSX"),
      hr(),selectInput("plot_metric","Obszar wykresu",choices=setNames(names(metric_labels),metric_labels),selected="capl_score"),
      plotOutput("group_plot",height="400px")
    ),
    tabPanel("Normy PAPL",
      br(),p("Zakresy referencyjne według płci i wieku, z raportu WF z AWF (tabele 56–62)."),
      selectInput("norm_metric","Wybierz obszar",choices=setNames(names(metric_labels),metric_labels)),
      DTOutput("norm_table"),
      p(class="small-note","Granice z raportu: pierwsza kategoria poniżej progu początkowego, druga do granicy progresji, trzecia do granicy kategorii sprawny, czwarta powyżej. Wyniki zaokrąglane do precyzji tabel.")
    ),
    tabPanel("Informacje",h3("Metodyka i prywatność"),
      p("CAPL-2: punktacja obliczana przez pakiet capl; kanadyjska klasyfikacja przez get_capl_interpretation()."),
      p("PAPL: progi z raportu „Aktywny dzisiaj dla zdrowia w przyszłości”, strony 130–134; bez przeliczania na nowe percentyle."),
      p("Moduł nie zastępuje oceny jakości danych i walidacji procedury adaptacyjnej."),
      p("W publicznym wdrożeniu dane przesłane do Shiny są przetwarzane na serwerze aplikacji. Nie przesyłaj danych identyfikujących dzieci."),
      tags$a(href="https://github.com/wieslawfirek/kalkulatorCAPL-PAPL", "Kod źródłowy na GitHubie",target="_blank")
    )
  )
)

server <- function(input, output, session) {
  individual <- eventReactive(input$calculate_one, {
    raw <- one_row(input)
    supplied <- lapply(c("pc_score","db_score","mc_score","ku_score"),function(k) value_or_na(input[[k]]))
    names(supplied) <- c("pc_score","db_score","mc_score","ku_score")
    process_data(raw,supplied)
  })
  group <- eventReactive(input$calculate_group,{
    req(input$excel)
    tryCatch({
      dat <- if (grepl("\\.csv$",input$excel$name,ignore.case=TRUE))
        read.csv(input$excel$datapath,stringsAsFactors=FALSE) else
        as.data.frame(readxl::read_excel(input$excel$datapath))
      # Explicitly supplied precomputed domain scores are not overwritten by missing raw data.
      supplied_keys <- intersect(c("pc_score","db_score","mc_score","ku_score","capl_score"),names(dat))
      computed <- process_data(dat)
      for(k in supplied_keys){
        value <- suppressWarnings(as.numeric(dat[[k]]))
        computed[[k]] <- ifelse(is.na(value),computed[[k]],value)
      }
      # Recompute both types of classifications from the final scores.
      for(k in metric_names){
        computed[[paste0("PAPL_",k)]] <- vapply(seq_len(nrow(computed)),function(i)
          papl_class(computed$age[i],computed$gender[i],get_metric(computed[i,,drop=FALSE],k),k),character(1))
        computed[[paste0("CAPL_",k)]] <- tryCatch(
          as.character(capl::get_capl_interpretation(computed$age,computed$gender,
            as.numeric(computed[[k]]),protocol_map[[k]])),
          error=function(e) rep(NA_character_,nrow(computed)))
      }
      computed
    },error=function(e) {showNotification(conditionMessage(e),type="error",duration=12);NULL})
  })
  display_cols <- function(d) {
    needed <- c("age","gender",metric_names,unlist(lapply(metric_names,function(k)c(paste0("PAPL_",k),paste0("CAPL_",k)))))
    d[,intersect(needed,names(d)),drop=FALSE]
  }
  output$individual_table <- renderDT({req(individual());datatable(display_cols(individual()),options=list(scrollX=TRUE,pageLength=5))})
  output$group_table <- renderDT({req(group());datatable(display_cols(group()),options=list(scrollX=TRUE,pageLength=10))})
  output$import_status <- renderText({
    d <- group()
    if (is.null(d)) return("Załaduj dane i wybierz „Oblicz grupę”.")
    paste("Wczytano",nrow(d),"wierszy. Brak wyniku ogólnego:",sum(is.na(d$capl_score)))
  })
  output$norm_table <- renderDT({
    d <- norms[norms$metric==input$norm_metric,c("sex","age","begin_max","progress_max","achieve_max")]
    colnames(d) <- c("Płeć","Wiek","Początkujący: próg następnej kat.","Dokonujący postępów: max","Sprawny: max")
    datatable(d,options=list(dom="t",paging=FALSE))
  })
  output$group_plot <- renderPlot({
    d<-group();req(d)
    k<-input$plot_metric;sc<-as.numeric(d[[k]]);inter<-as.character(d[[paste0("CAPL_",k)]])
    ok<-!is.na(sc)&!is.na(inter)
    validate(need(sum(ok)>0,"Brak wyników do wykresu według norm kanadyjskich."))
    capl::get_capl_bar_plot(score=sc[ok], interpretation=inter[ok],
      x_label="Kategorie CAPL-2", y_label=metric_labels[[k]])
  })
  output$individual_plot <- renderPlot({
    d<-individual();req(d)
    score<-as.numeric(unlist(d[1,c("pc_score","db_score","mc_score","ku_score"),drop=FALSE]))
    validate(need(any(!is.na(score)),"Brak wyników domenowych do wykresu."))
    ggplot(data.frame(domain=factor(names(score),levels=names(score)),value=score),
      aes(x=domain,y=value)) + geom_col(fill="#2879aa",na.rm=TRUE) +
      labs(x=NULL,y="Wynik punktowy",title="Wyniki domenowe") + theme_minimal()
  })
  output$template <- downloadHandler(filename=function() "CAPL2_szablon.xlsx",
    content=function(file){
      dat <- capl::get_capl_demo_data(1)
      dat[1,] <- NA
      writexl::write_xlsx(dat,file)
    })
  output$save_group <- downloadHandler(filename=function() "PAPL_wyniki_grupa.xlsx",
    content=function(file){req(group());writexl::write_xlsx(group(),file)})
  output$save_individual <- downloadHandler(filename=function() "PAPL_wynik_dziecka.xlsx",
    content=function(file){req(individual());writexl::write_xlsx(individual(),file)})
}
shinyApp(ui,server)
