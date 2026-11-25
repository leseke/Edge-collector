import { chromium } from "playwright";
import { mkdir, writeFile } from "node:fs/promises";
const base="https://edge-radar-preview-1c14d55.ylan-seke.workers.dev";
const routes=[["home","/","Vue d’ensemble"],["explorer","/explorer","Explorer"],["radar","/mri?tab=signaux","Radar Pokémon"],["offers","/mri?tab=offres","Offres ouvertes"],["sales","/mri?tab=ventes","Ventes"],["market","/mri?tab=marche","Tendances du marché"],["portfolio","/portfolio","Portefeuille"],["follow","/follow","Suivi"]];
const out=process.env.EDGE_SCREENSHOTS_DIR||"edge-ui-report";
await mkdir(out,{recursive:true});
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
    await page.getByRole("heading",{name:heading,exact:false}).first().waitFor({timeout:45000});
    await page.evaluate(()=>document.fonts.ready);
    const geometry=await page.evaluate(()=>({width:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth,nav:[...document.querySelectorAll(".side-nav a")].map(a=>({text:a.textContent.trim(),width:a.getBoundingClientRect().width,height:a.getBoundingClientRect().height})),palette:getComputedStyle(document.documentElement).getPropertyValue("--app-bg").trim()}));
    result.checks.push(["http",result.status===200],["no horizontal overflow",geometry.scroll<=geometry.width+1],["five navigation destinations",geometry.nav.length===5],["V3 palette",geometry.palette==="#080e19"],["touch targets",viewport.width!==390||geometry.nav.every(a=>a.width>=44&&a.height>=44)]);
    if(name==="explorer"){await page.getByRole("button",{name:"Liste",exact:true}).click();result.checks.push(["list mode",await page.locator(".edge-explorer-premium").getAttribute("data-view")==="list"]);await page.getByRole("button",{name:"Grille",exact:true}).click();result.checks.push(["grid mode",await page.locator(".edge-explorer-premium").getAttribute("data-view")==="grid"]);}
    await page.screenshot({path:out+"/"+viewport.width+"-"+name+".png",animations:"disabled",timeout:20000});
   }catch(e){errors.push(String(e));}
   result.ok=errors.length===0&&result.checks.length>0&&result.checks.every(c=>c[1]);
   results.push(result);await page.close();
  }
  await context.close();
 }
}finally{await browser.close();await writeFile(out+"/results.json",JSON.stringify(results,null,2));}
console.log(JSON.stringify(results.map(({name,viewport,ok,status,checks,errors})=>({name,width:viewport.width,ok,status,checks,errors})),null,2));
if(results.some(r=>!r.ok))process.exitCode=1;
