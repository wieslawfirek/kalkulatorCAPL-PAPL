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
# Original bar graphic; use valid nonmissing CAPL classifications.
k<-"capl_score";i<-"capl_interpretation"
ok<-!is.na(a[[k]]) & !is.na(a[[i]])
if(any(ok)){
 png(tempfile(fileext=".png"))
 p<-capl::get_capl_bar_plot(score=a[[k]][ok],
  interpretation=a[[i]][ok],x_label="CAPL",y_label="Score")
 if(inherits(p,"ggplot"))print(p)
 dev.off()
}
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
# Test the eight derived plots and original CAPL plot.
for (type in unname(plot_choices)) {
  png(tempfile(fileext=".png"))
  tryCatch({p<-research_plot(a,type,"capl_score");print(p)},
    finally=dev.off())
}
cat("BATCH SMOKE TEST PASS: reproducibility, input/output, original graphic, optional PAPL\n")
