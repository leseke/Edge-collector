// Read-only operational audit: fixed aggregate SELECTs, no customer data, no secrets in output.
import {writeFile} from "node:fs/promises";
const token=process.env.CLOUDFLARE_API_TOKEN;
if(!token)throw Error("missing_cloudflare_token");
async function cf(path,sql){
 const response=await fetch("https://api.cloudflare.com/client/v4"+path,{signal:AbortSignal.timeout(15000),headers:{Authorization:"Bearer "+token,"Content-Type":"application/json"},...(sql?{method:"POST",body:JSON.stringify({sql})}:{})});
 if(!response.ok)throw Error("http_"+response.status);
 const data=await response.json();if(data.success!==true)throw Error("api_failure");return data.result;
}
const accounts=await cf("/accounts?per_page=100");
if(accounts.length!==1||! /^[a-f0-9]{32}$/i.test(accounts[0].id))throw Error("ambiguous_account");
const base="/accounts/"+accounts[0].id+"/d1/database";
const matches=(await cf(base+"?per_page=100")).filter(d=>d.name==="edge-tcg-history");
if(matches.length!==1||! /^[a-f0-9-]{36}$/i.test(matches[0].uuid))throw Error("ambiguous_database");
const queries={
 paid_sales:"SELECT COUNT(*) AS total,MAX(collected_at) AS latest FROM paid_market_sales",
 offers:"SELECT kind,COUNT(*) AS total,MAX(observed_at) AS latest FROM gcc_offer_observations GROUP BY kind",
 coverage:"SELECT kind,COUNT(*) AS total,MAX(completed_at) AS latest FROM gcc_complete_cycles GROUP BY kind",
 alerts:"SELECT COUNT(*) AS total,MAX(observed_at) AS latest FROM gcc_research_alerts",
 discoveries:"SELECT publisher,COUNT(*) AS total,MAX(first_seen_at) AS latest FROM catalyst_discoveries GROUP BY publisher",
 investigations:"SELECT status,COUNT(*) AS total,MAX(observed_at) AS latest FROM catalyst_investigations GROUP BY status",
 commercial:"SELECT merchant,status,COUNT(*) AS total,MAX(observed_at) AS latest FROM commercial_research_observations GROUP BY merchant,status",
 publisher_scans:"SELECT publisher,status,COUNT(*) AS total,MAX(observed_at) AS latest FROM catalyst_scan_runs GROUP BY publisher,status"
};
const report={observedAt:new Date().toISOString(),checks:{}};
for(const [name,sql] of Object.entries(queries)){
 try{const result=await cf(base+"/"+matches[0].uuid+"/query",sql);if(result.length!==1||result[0].success!==true||!Array.isArray(result[0].results))throw Error("invalid_result");report.checks[name]={status:"OK",rows:result[0].results};}
 catch{report.checks[name]={status:"UNAVAILABLE",rows:[]};}
}
console.log(JSON.stringify(report,null,2));
if(process.argv[2])await writeFile(process.argv[2],JSON.stringify(report,null,2),{mode:0o600});
if(Object.values(report.checks).some(c=>c.status!=="OK"))process.exitCode=1;
