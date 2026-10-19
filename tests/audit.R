options(warn=1)
library(capl)
source("app.R",local=TRUE)
set.seed(145)
raw <- capl::get_capl_demo_data(n=120)
set.seed(20261018)
baseline <- capl::get_capl(raw_data=raw,sort="asis")
out <- run_capl(raw,with_papl=TRUE)
stopifnot(nrow(baseline)==nrow(out))
stopifnot(all(names(baseline)%in%names(out)))
stopifnot(all(capl_derived %in% names(out)),length(capl_derived)==40)
errors<-character()
for(k in names(baseline)){
  equal<-isTRUE(all.equal(baseline[[k]],out[[k]],check.attributes=FALSE,tolerance=1e-8))
  if(!equal) errors<-c(errors,paste("Mismatch",k))
}
cat("INPUT RECORDS:",nrow(raw),"\n")
cat("ORIGINAL CAPL COLUMNS:",ncol(baseline),"\n")
cat("DERIVED CAPL OUTPUT COLUMNS:",length(intersect(capl_derived,names(out))),"\n")
cat("ADDITIONAL POLISH REFERENCE COLUMNS:",length(grep("^PAPL_",names(out))),"\n")
cat("ORIGINAL CAPL PARITY ERRORS:",length(errors),"\n")
if(length(errors))cat(paste(errors,collapse="\n"),"\n")
# Test normative thresholds for every available reference row.
count<-0
for(i in seq_len(nrow(norms))){
  n<-norms[i,]
  step<-if(n$metric %in% c("pacer_20m_laps","camsa_skill_time_score","step_average","self_report_pa")) 1 else 0.1
  vals<-c(n$begin_max-step,n$begin_max,n$progress_max,
     n$progress_max+step,n$achieve_max,n$achieve_max+step)
  expected<-c(1,2,2,3,3,4)
  got<-vapply(vals,function(v) match(papl_class(n$age,n$sex,v,n$metric),levels_pl),integer(1))
  if(!identical(as.integer(got),as.integer(expected)))
    errors<-c(errors,paste("PAPL threshold",i,n$metric,n$sex,n$age))
  count<-count+1
}
cat("POLISH REFERENCE ROWS TESTED:",count,"\n")
cat("TOTAL ERRORS:",length(errors),"\n")
write.csv(data.frame(check=if(length(errors))errors else "CAPL and PAPL parity",
 status=if(length(errors))"FAIL" else "PASS"),"audit-results.csv",row.names=FALSE)
if(length(errors))stop("AUDIT FAILURE")
