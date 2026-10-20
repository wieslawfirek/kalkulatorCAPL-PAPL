library(capl)
library(readxl)
library(writexl)
source("app.R",local=TRUE)
raw <- capl::get_capl_demo_data(n=50)
a<-run_capl(raw,TRUE)
b<-run_capl(raw,TRUE)
stopifnot(identical(a,b))
stopifnot(all(names(capl::get_capl(raw))%in%names(a)))
set.seed(42); before<-.Random.seed
invisible(run_capl(raw,FALSE))
stopifnot(identical(before,.Random.seed))
stopifnot(!any(grepl("^PAPL_",names(run_capl(raw,FALSE)))))
file<-tempfile(fileext=".xlsx");writexl::write_xlsx(raw,file)
roundtrip<-as.data.frame(readxl::read_excel(file))
out<-run_capl(roundtrip,TRUE)
stopifnot(isTRUE(all.equal(a,out,check.attributes=FALSE)))
export<-tempfile(fileext=".xlsx");writexl::write_xlsx(out,export)
returned<-as.data.frame(readxl::read_excel(export))
stopifnot(nrow(returned)==nrow(out),all(names(out)%in%names(returned)))
# New CAPL-2 codebook and multi-sheet research workbook.
cb <- codebook(original_fields)
stopifnot(nrow(cb)==60,identical(as.character(cb$Zmienna),original_fields),
  all(c("Dopuszczalne_wartosci","Znaczenie_kodow","Uwagi") %in% names(cb)),
  all(nzchar(cb$Dopuszczalne_wartosci)),
  identical(cb$Dopuszczalne_wartosci[cb$Zmienna=="csappa1"],"1, 2, 3, 4"))
tables <- research_tables(a,"capl_score")
stopifnot(all(c("Profil domen","Kategorie","Kategorie wg plci",
 "Kategorie wg wieku","Status domen","Braki") %in% names(tables)))
report <- tempfile(fileext=".xlsx")
writexl::write_xlsx(c(list("Pelne wyniki"=a,"Ksiazka kodow"=cb),tables),report)
stopifnot(all(c("Pelne wyniki","Ksiazka kodow","Kategorie","Status domen") %in%
 readxl::excel_sheets(report)))
stopifnot(nrow(readxl::read_excel(report,sheet="Pelne wyniki"))==nrow(a))
stopifnot(all(c("Opis ogolem","Opis wiek plec") %in% names(tables)))
stopifnot(all(c("Srednia","SD","Mediana","Q1","Q3","Minimum","Maksimum","Braki") %in% names(tables[["Opis ogolem"]])))
complete_stats <- all_numeric_summaries(a)
stopifnot(nrow(complete_stats)>15,
  all(c("capl_score","pc_score","db_score","mc_score","ku_score") %in% complete_stats$Wskaznik),
  !("pacer_lap_distance" %in% complete_stats$Wskaznik),
  !("age" %in% complete_stats$Wskaznik),
  !("csappa1" %in% complete_stats$Wskaznik))
freq <- input_frequencies(a)
stopifnot("pacer_lap_distance" %in% freq$Zmienna)
per_child <- participant_completeness(a,original_fields)
stopifnot(nrow(per_child)==nrow(a),
  all(c("capl_status","Braki_w_przeslanych_polach","Wynik_ogolny_dostepny") %in% names(per_child)))
cat("BATCH SMOKE TEST PASS: reproducibility, input/output, descriptive tables, optional PAPL\n")
