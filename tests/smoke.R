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
cat("BATCH SMOKE TEST PASS: reproducibility, input/output, original graphic, optional PAPL\n")
