options(warn=1)
library(capl)
source("app.R", local=TRUE)
set.seed(142)
raw <- capl::get_capl_demo_data(n=120)
# CAPL's synthetic data may include ages outside the Polish normative range.
# Limit the parity comparison to the documented common age range.
raw <- raw[!is.na(raw$age) & raw$age %in% 8:12, , drop=FALSE]
stopifnot(nrow(raw) > 0)
baseline <- capl::get_capl(raw)
repeat_direct <- capl::get_capl(raw)
out <- process_data(raw)
# Diagnostic comparison to detect nondeterministic reference scores.
compare_cols <- intersect(c("db_score","capl_score"),names(baseline))
for (key in compare_cols) {
  a <- baseline[[key]]; b <- repeat_direct[[key]]
  mismatches <- which((is.na(a)!=is.na(b)) | (!is.na(a)&!is.na(b)&abs(a-b)>1e-8))
  cat("DIRECT REPEAT:",key,"mismatches",length(mismatches),"rows:",paste(head(mismatches,15),collapse=","),"\n")
}

numeric_keys <- intersect(c("pacer_20m_laps","pacer_score","plank_score","camsa_score",
 "pc_score","db_score","mc_score","ku_score","capl_score"),names(baseline))
stopifnot(nrow(out)==nrow(baseline))
summary <- data.frame(check=character(), status=character(), detail=character())
record <- function(name, ok, detail="") {
  summary <<- rbind(summary,data.frame(check=name,status=if(ok) "PASS" else "FAIL",detail=detail))
}
for (k in numeric_keys) {
 a<-baseline[[k]]; b<-out[[k]]
 equal <- isTRUE(all.equal(as.numeric(a),as.numeric(b),check.attributes=FALSE,tolerance=1e-8))
 bad <- which((is.na(a) != is.na(b)) | (!is.na(a) & !is.na(b) & abs(a-b)>1e-8))
 record(paste0("CAPL numeric ",k),equal,
   paste("Rows:",length(a)," mismatches:",length(bad)," examples:",
   paste(head(sprintf("row%d: %s vs %s",bad,as.character(a[bad]),as.character(b[bad])),8),collapse="; ")))
}
# Compare original classification fields on all available valid scores
for(k in c("capl","pc","db","mc","ku")) {
 score_key <- paste0(k,"_score")
 if(!score_key %in% names(out))next
 expected<-capl::get_capl_interpretation(out$age,out$gender,out[[score_key]],k)
 actual<-out[[paste0("CAPL_",score_key)]]
 record(paste0("CAPL interpretation ",k),identical(as.character(expected),as.character(actual)))
}
# Polish reference boundary tests: exact matches and values either side.
for(i in seq_len(nrow(norms))) {
  n<-norms[i,]
  one_unit <- if(n$metric %in% c("pacer_20m_laps","camsa_skill_time_score","step_average","self_report_pa")) 1 else 0.1
  v<-c(n$begin_max-one_unit,n$begin_max,n$progress_max,n$progress_max+one_unit,n$achieve_max,n$achieve_max+one_unit)
  expected<-c(1,2,2,3,3,4)
  observed<-vapply(v,function(z) match(papl_class(n$age,n$sex,z,n$metric),levels_pl),integer(1))
  record(paste0("PAPL boundaries ",n$sex," ",n$age," ",n$metric),
    isTRUE(all(observed == expected)),paste("expected:",paste(expected,collapse="/"),"actual:",paste(observed,collapse="/")))
}
# Real import from the generated demo sample, same 60 columns.
file<-tempfile(fileext=".xlsx")
writexl::write_xlsx(raw,file)
imported<-as.data.frame(readxl::read_excel(file))
imported_out<-process_data(imported)
xa<-as.numeric(baseline$capl_score); xb<-as.numeric(imported_out$capl_score)
bad_import<-which(is.na(xa)!=is.na(xb) | (!is.na(xa)&!is.na(xb)&abs(xa-xb)>1e-8))
record("XLSX import numeric comparison",length(bad_import)==0,
paste("mismatches:",length(bad_import),"examples:",
paste(head(sprintf("row%d: %s vs %s",bad_import,as.character(xa[bad_import]),as.character(xb[bad_import])),8),collapse="; ")))
# Check individual form data with a minimal set of values
manual<-data.frame(age=10,gender="Girl",pacer_lap_distance=20,pacer_laps=25,
 plank_time=75,camsa_skill_score1=10,camsa_time1=25,
 camsa_skill_score2=11,camsa_time2=23,self_report_pa=5)
manual_out<-process_data(manual)
record("Manual raw-data CAPL parity",isTRUE(all.equal(
 capl::get_capl(manual)$pc_score,manual_out$pc_score,check.attributes=FALSE)))
write.csv(summary,"audit-results.csv",row.names=FALSE,fileEncoding="UTF-8")
# Reproducible diagnostics limited to synthetic demo records.
idx <- unique(c(46,80))
idx <- idx[idx <= nrow(raw)]
diag <- data.frame(row=idx, baseline_db=baseline$db_score[idx],
  second_direct_db=repeat_direct$db_score[idx], application_db=out$db_score[idx],
  baseline_capl=baseline$capl_score[idx],
  second_direct_capl=repeat_direct$capl_score[idx],
  application_capl=out$capl_score[idx],
  excel_capl=imported_out$capl_score[idx])
write.csv(diag,"audit-diagnostics.csv",row.names=FALSE)
write.csv(raw[idx,,drop=FALSE],"audit-input-cases.csv",row.names=FALSE)

cat("\nAUDIT RESULTS:\n");print(summary[summary$status=="FAIL",],row.names=FALSE)
cat("\nPassed:",sum(summary$status=="PASS"),"/",nrow(summary),"\n")
if(any(summary$status=="FAIL"))stop("AUDIT HAS FAILURES: inspect audit-results.csv")
