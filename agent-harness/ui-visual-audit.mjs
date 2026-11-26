import { chromium } from "playwright";
import { mkdir, writeFile } from "node:fs/promises";
const base="https://edge-radar-preview-1c14d55.ylan-seke.workers.dev";
const routes=[["home","/","Vue d’ensemble"],["explorer","/explorer","Explorer"],["radar","/mri?tab=signaux","Radar Pokémon"],["offers","/mri?tab=offres","Offres ouvertes"],["sales","/mri?tab=ventes","Ventes"],["market","/mri?tab=marche","Tendances du marché"],["portfolio","/portfolio","Portefeuille"],["follow","/follow","Suivi"]];
const out=process.env.EDGE_SCREENSHOTS_DIR||"edge-ui-report";
await mkdir(out,{recursive:true});
const expected=process.env.EDGE_EXPECTED_REVISION||null;
let version=null;
try{
 const response=await fetch(base+"/api/version",{cache:"no-store",signal:AbortSignal.timeout(20000)});
 if(!response.ok)throw Error("Version endpoint HTTP "+response.status);
 version=await response.json();
 if(version.application!=="EDGE"||version.design!=="v3"||!(/^[a-f0-9]{40}$/.test(version.revision))||(expected&&version.revision!==expected))throw Error("Unexpected deployed revision");
 await writeFile(out+"/version.json",JSON.stringify({ok:true,expected,actual:version},null,2));
}catch(error){
 const report={ok:false,expected,actual:version,error:String(error)};
 await writeFile(out+"/version.json",JSON.stringify(report,null,2));
 console.error("DEPLOYMENT MISMATCH",JSON.stringify(report));
 process.exit(1);
}
const browser=await chromium.launch({headless:true});
const results=[];
try{
 for(const viewport of [{width:390,height:844},{width:1440,height:900}]){
  const context=await browser.newContext({viewport,deviceScaleFactor:1,isMobile:viewport.width===390,hasTouch:viewport.width===390});
  for(const [name,path,heading] of routes){
   const page=await context.newPage();
   const errors=[];page.on("pageerror",e=>errors.push(e.message));
   const result={name,viewport,status:null,errors,checks:[]};
   try{
    const response=await page.goto(base+path,{waitUntil:"domcontentloaded",timeout:60000});
    result.status=response?.status()??null;
    if(result.status!==200)throw Error("HTTP "+result.status);
    await page.getByRole("heading",{name:heading,exact:false}).first().waitFor({timeout:45000});
    await page.evaluate(()=>Promise.race([document.fonts.ready,new Promise(resolve=>setTimeout(resolve,5000))]));
    const geometry=await page.evaluate(()=>({width:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth,nav:[...document.querySelectorAll(".side-nav a")].map(a=>({text:a.textContent.trim(),width:a.getBoundingClientRect().width,height:a.getBoundingClientRect().height})),palette:getComputedStyle(document.documentElement).getPropertyValue("--app-bg").trim()}));
    result.geometry=geometry;
    result.checks.push(["http",result.status===200],["no horizontal overflow",geometry.scroll<=geometry.width+1],["five navigation destinations",geometry.nav.length===5],["V3 palette",geometry.palette==="#080e19"],["touch targets",viewport.width!==390||geometry.nav.every(a=>a.width>=44&&a.height>=44)]);
    if(name==="home"){
     const layout=await page.evaluate(()=>{
      const search=document.querySelector(".edge-v3-search"),input=search?.querySelector("input"),metrics=document.querySelector(".edge-v3-metrics"),summary=document.querySelector(".edge-v3-market-summary"),tiles=[...document.querySelectorAll(".edge-v3-metrics>a")];
      const display=e=>e?getComputedStyle(e).display:null;
      return {searchDisplay:display(search),searchWidth:search?.getBoundingClientRect().width??0,inputWidth:input?.getBoundingClientRect().width??0,summaryBorder:summary?parseFloat(getComputedStyle(summary).borderTopWidth):0,metricsDisplay:display(metrics),tileDisplays:tiles.map(display),tileCount:tiles.length,art:[...document.querySelectorAll(".edge-v3-asset-art")].map(e=>{const b=e.getBoundingClientRect();return {width:b.width,height:b.height};})};
     });
     result.homeLayout=layout;
     result.checks.push(["home search styled",layout.searchDisplay==="flex"&&layout.searchWidth>=250&&layout.inputWidth>=120],["home summary styled",layout.summaryBorder>=1],["home metrics grid",layout.metricsDisplay==="grid"&&layout.tileCount===3&&layout.tileDisplays.every(d=>d==="flex")],["home artwork proportions",layout.art.every(a=>a.width>0&&Math.abs(a.height/a.width-1.4)<0.12)]);
    }
    if(name==="explorer"){await page.getByRole("button",{name:"Liste",exact:true}).click();result.checks.push(["list mode",await page.locator(".edge-explorer-premium").getAttribute("data-view")==="list"]);await page.getByRole("button",{name:"Grille",exact:true}).click();result.checks.push(["grid mode",await page.locator(".edge-explorer-premium").getAttribute("data-view")==="grid"]);}
   }catch(e){errors.push(String(e));}
   finally{try{await page.screenshot({path:out+"/"+viewport.width+"-"+name+".png",animations:"disabled",timeout:20000});}catch(e){errors.push("Screenshot: "+String(e));}}
   result.ok=errors.length===0&&result.checks.length>0&&result.checks.every(c=>c[1]);
   results.push(result);await page.close();
  }
  await context.close();
 }
}finally{await browser.close();await writeFile(out+"/results.json",JSON.stringify(results,null,2));}
console.log(JSON.stringify(results.map(({name,viewport,ok,status,checks,errors})=>({name,width:viewport.width,ok,status,checks,errors})),null,2));
if(results.some(r=>!r.ok))process.exitCode=1;
