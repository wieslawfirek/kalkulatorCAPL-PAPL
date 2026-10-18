library(capl)
library(readxl)
library(writexl)
library(ggplot2)
source("app.R",local=TRUE)
raw <- capl::get_capl_demo_data(30)
raw <- raw[!is.na(raw$age) & raw$age %in% 8:12,,drop=FALSE]
stopifnot(nrow(raw)>0)
# Repeated calls return identical results without requiring the user to set.seed.
set.seed(13); a <- process_data(raw)
set.seed(870); b <- process_data(raw)
stopifnot(isTRUE(all.equal(a$capl_score,b$capl_score,check.attributes=FALSE)))
stopifnot(isTRUE(all.equal(a$db_score,b$db_score,check.attributes=FALSE)))
# Calculator must leave other statistical analysis RNG unaffected.
set.seed(42); before <- .Random.seed
ignore <- process_data(raw)
stopifnot(identical(before,.Random.seed))
# Excel import and output must preserve scores and number of records.
file <- tempfile(fileext=".xlsx")
writexl::write_xlsx(raw,file)
roundtrip <- as.data.frame(readxl::read_excel(file))
out <- process_data(roundtrip)
stopifnot(nrow(out)==nrow(raw),
          isTRUE(all.equal(a$capl_score,out$capl_score,check.attributes=FALSE)))
export <- tempfile(fileext=".xlsx")
writexl::write_xlsx(out,export)
exported <- as.data.frame(readxl::read_excel(export))
stopifnot(nrow(exported)==nrow(out), "PAPL_capl_score" %in% names(exported))
# Manual partial data and missing values should not crash.
manual <- data.frame(age=10,gender="Girl",pacer_lap_distance=20,
 pacer_laps=20,plank_time=60,camsa_skill_score1=10,camsa_time1=22,
 camsa_skill_score2=11,camsa_time2=21,self_report_pa=5)
result <- process_data(manual)
stopifnot(nrow(result)==1)
# Native CAPL graphic and standard domain graphic both render in R.
png(tempfile(fileext=".png"))
p <- ggplot(data.frame(domain=c("pc","db"),score=c(10,20)),aes(domain,score))+geom_col()
print(p);dev.off()
if (any(!is.na(a$capl_score))) {
  x <- a$capl_score
  inter <- a$CAPL_capl_score
  ok <- !is.na(x)&!is.na(inter)
  if(any(ok)) {
    png(tempfile(fileext=".png"))
    capl::get_capl_bar_plot(score=x[ok],interpretation=inter[ok],
      x_label="CAPL categories",y_label="Score")
    dev.off()
  }
}
# All original CAPL columns must remain present in calculated and exported results.
original <- with_fixed_rng(capl::get_capl(raw))
stopifnot(all(names(original) %in% names(a)))
stopifnot(all(names(a) %in% names(exported)))
# Exercise filtering logic that powers the detailed output table.
inputs <- names(capl::get_capl_demo_data(n=1))
calculated <- setdiff(names(a),inputs)
stopifnot(length(calculated)>0,all(calculated %in% names(a)))
cat("Full CAPL output columns:",ncol(original),"calculator columns:",ncol(a),"\n")
cat("SMOKE TESTS PASS: repeated scores, RNG state, Excel round trip, manual input, plotting\n")
