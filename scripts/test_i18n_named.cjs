const fs = require('node:fs'), vm = require('node:vm'), path = require('node:path');
const root = path.resolve(__dirname, '..');
async function runtime(code, dict, lang) {
  const ctx = {window:{}, document:{currentScript:{src:'http://local/i18n/i18n.js'},readyState:'complete',documentElement:{},title:'EnergyWizard',body:{nodeType:1,tagName:'BODY',hasAttribute:()=>false,getAttribute:()=>null,firstChild:null}},
    localStorage:{getItem:()=>null},fetch:async url=>({ok:true,json:async()=>url.endsWith('config')?{languages:{sv:'Svenska',en:'English',cs:'Čeština'},default:lang,chosen:true}:dict}),
    MutationObserver:class{observe(){} disconnect(){}}, requestAnimationFrame:()=>{}};
  vm.createContext(ctx);vm.runInContext(code,ctx);await ctx.window.I18N.ready;return ctx.window.I18N;
}
(async()=>{
 const code=fs.readFileSync(path.join(root,'smartbox/i18n/i18n.js'),'utf8');
 const dict={'Första telefonen i Home Assistant ({name})':'První telefon ({name})','Avgifter vid köp ({currency}/kWh, inkl. moms)':'Poplatky ({currency}/kWh)',
 'Kontakt mellan {server} och {car}':'Auto {car}, server {server}','Valuta {unit} och {unit}':'Měna {unit} a {unit}',
 'Kontakt med {name}':'Kontakt {wrong}','Pris ({unit}): {value}.':'Cena ({unit}): {value}.','Laddar # kW':'Charging # kW','till {service}':'pro {service}'};
 const checks=[['Första telefonen i Home Assistant (mobile_app_michal_ipad)','První telefon (mobile_app_michal_ipad)'],['Avgifter vid köp (Kč/kWh, inkl. moms)','Poplatky (Kč/kWh)'],
 ['Kontakt mellan HA och bilen','Auto bilen, server HA'],['Valuta Kč och Kč','Měna Kč a Kč'],['Valuta Kč och EUR','Valuta Kč och EUR'],['Kontakt med HA','Kontakt med HA'],
 ['Pris (Kč): -1,25.','Cena (Kč): -1,25.'],['Pris xKčx: -1,25x','Pris xKčx: -1,25x'],['Laddar 3,7 kW','Charging 3.7 kW'],['till notify.mobile_app_michal','pro notify.mobile_app_michal']];
 const I=await runtime(code,dict,'cs');let count=0;
 for(const [input,expected] of checks){if(I.tr(input)!==expected)throw Error(JSON.stringify({input,expected,actual:I.tr(input)}));count++;}
 const sv=await runtime(code,dict,'sv');for(const [input] of checks){if(sv.tr(input)!==input)throw Error('Swedish changed');count++;}
 const en=await runtime(code,{},'en');if(en.tr('Hej, Michal!')!=='Hello, Michal!')throw Error('English legacy rule changed');count++;
 // Compare old/new runtimes with the same original catalog when an optional baseline is supplied.
 if(process.argv[2]&&process.argv[3]){
   const baseline=fs.readFileSync(process.argv[2],'utf8'), catalog=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
   const old=await runtime(baseline,catalog,'en'), fresh=await runtime(code,catalog,'en');
   for(const key of Object.keys(catalog).filter(k=>!k.startsWith('_'))){const input=key.replace(/#/g,'17');if(old.tr(input)!==fresh.tr(input))throw Error('Regression: '+key);count++;}
 }
 console.log(JSON.stringify({checks:count,failed:0}));
})().catch(e=>{console.error(e);process.exitCode=1;});
