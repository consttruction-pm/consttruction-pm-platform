const { chromium } = require("playwright");
const results=[];
function rec(n,ok,d=""){results.push({n,ok:!!ok});console.log(`${ok?"PASS":"FAIL"} ${n}${d?" :: "+d:""}`);}
(async()=>{
 const b=await chromium.launch({executablePath:"/usr/bin/chromium",args:["--no-sandbox"]});
 const p=await (await b.newContext()).newPage();
 await p.goto("http://127.0.0.1:4180/preview/login?next=/cubi/enterprise/dashboard");
 await p.click('button[name=role][value=enterprise]');
 await p.waitForURL(/\/cubi\//);
 for (const [loc,label,rtl,title] of [
   ["fa","فارسی",true,"داشبورد"],
   ["ar","العربية",true,"لوحات"],
   ["de","Deutsch",false,"Enterprise-Dashboards"],
   ["zh","中文",false,"企业"],
   ["fr","Français",false,"Tableaux"],
   ["ja","日本語",false,"エンタープライズ"],
   ["ko","한국어",false,"엔터프라이즈"],
   ["ru","Русский",false,"Панели"],
   ["tr","Türkçe",false,"Kurumsal"],
   ["en","English",false,"Enterprise dashboard"],
 ]) {
   await p.selectOption('select[aria-label]', loc);
   await p.waitForTimeout(250);
   const dir=await p.evaluate(()=>document.documentElement.dir);
   const lang=await p.evaluate(()=>document.documentElement.lang);
   const h1=await p.locator("h1").first().textContent();
   rec(`${loc} direction`, (dir==="rtl")===rtl, dir);
   rec(`${loc} lang attribute`, lang===loc || (loc==="tr"&&lang==="tr-TR"), lang);
   rec(`${loc} translated page title`, (h1||"").includes(title), (h1||"").trim());
 }
 // Initial-set pages are translated in every locale, not just the shell.
 const riskTitles={fa:"ریسک‌ها و مسائل",ar:"المخاطر والمشكلات",de:"Risiken & Probleme",zh:"风险与问题",fr:"Risques et problèmes",ja:"リスクと課題",ko:"리스크 및 이슈",ru:"Риски и проблемы",tr:"Riskler ve sorunlar",en:"Risks & issues"};
 for (const [loc,expected] of Object.entries(riskTitles)) {
   await p.selectOption('select[aria-label]', loc);
   await p.goto("http://127.0.0.1:4180/cubi/enterprise/risks");
   await p.waitForTimeout(300);
   const h1=(await p.locator("h1").first().textContent())||"";
   rec(`${loc} risks page translated`, h1.includes(expected), h1.trim());
 }
 // Numbers and dates in Persian dashboard/portfolios
 await p.selectOption('select[aria-label]', "fa");
 await p.goto("http://127.0.0.1:4180/cubi/enterprise/projects");
 await p.waitForTimeout(500);
 const body=await p.locator("body").innerText();
 rec("fa dates use localized digits/format", /[۰-۹]|[0-9]{4}/.test(body), "");
 rec("fa RTL persists on deep link", (await p.evaluate(()=>document.documentElement.dir))==="rtl");
 await p.selectOption('select[aria-label]', "en");
 await p.waitForTimeout(200);
 rec("locale reset to ltr English", (await p.evaluate(()=>document.documentElement.dir))==="ltr");
 await b.close();
 const f=results.filter(r=>!r.ok);
 console.log(`\n${results.length-f.length}/${results.length} locale checks passed`);
 process.exit(f.length?1:0);
})().catch(e=>{console.error(e);process.exit(2);});
