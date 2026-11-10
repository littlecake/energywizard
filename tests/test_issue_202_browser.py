"""Use the real browser dictionary/translator and both toast implementations, with no network."""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which('node') is None, reason='Node.js required for browser translation checks')
def test_settings_and_toasts_translate_without_waiting_for_dom_observer():
    js = r'''
const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
const dictionary = JSON.parse(fs.readFileSync('smartbox/i18n/en.json', 'utf8'));
async function browser(language) {
  const el = {textContent:'', style:{setProperty(){}}, classList:{add(){},remove(){}},
    setAttribute(){},removeAttribute(){},addEventListener(){}};
  const ctx = vm.createContext({console, document:{readyState:'loading',currentScript:null,
    documentElement:el,getElementById:()=>el,querySelector:()=>el,addEventListener(){}},
    localStorage:{getItem:()=>language}, navigator:{}, location:{search:''},
    URLSearchParams, innerWidth:400,innerHeight:800, history:{replaceState(){}},
    addEventListener(){}, matchMedia:()=>({matches:true}), setTimeout(){},clearTimeout(){},setInterval(){},
    fetch:async(url)=>({ok:true,json:async()=>url.endsWith('config')?{default:language,languages:{sv:'Svenska',en:'English'}}:dictionary})});
  ctx.window=ctx;
  vm.runInContext(fs.readFileSync('smartbox/i18n/i18n.js','utf8'),ctx);
  await ctx.I18N.ready;
  return {ctx,el};
}
(async()=>{
  const examples = [
    ['Använd effektsensorn sensor.p1_zendure_api','Use power sensor sensor.p1_zendure_api'],
    ['Smartmätare: sensor.p1_zendure_api (okänt märke)','Smart meter: sensor.p1_zendure_api (unknown brand)'],
    ['hittades (Zendure) - ingen drivrutin än, bidra gärna','found (Zendure) - no driver yet; contributions welcome'],
    ['1 prissensor hittades i Home Assistant.','1 price sensor found in Home Assistant.'],
    ['3 prissensorer hittades i Home Assistant.','3 price sensors found in Home Assistant.'],
    ['🔌 Batteri eller växelriktare utan Home Assistant-integration','🔌 Battery or inverter without a Home Assistant integration'],
    ['som husbatteri','as a home battery'],['Senaste skanningen','Last scan'],
    ['Laddningen av Laddaren 42 har startat med 7.2 kW.','Charging Laddaren 42 started at 7.2 kW.']
  ];
  for(const [file,start] of [['webdashboard/static/app.js','boot'],['ewapp/static/app.js','start']]) {
    for(const language of ['en','sv']) {
      const {ctx,el}=await browser(language);
      for(const [source,expected] of examples) assert.equal(ctx.I18N.tr(source),language==='en'?expected:source);
      let code=fs.readFileSync(file,'utf8');
      code=code.replace(new RegExp('\\n'+start+'\\(\\);\\s*$'),'');
      vm.runInContext(code,ctx);
      vm.runInContext('toast("Priskällan sparad - priserna hämtas om inom en minut")',ctx);
      assert.equal(el.textContent,language==='en'?'Price source saved - prices will be fetched again within a minute':'Priskällan sparad - priserna hämtas om inom en minut');
    }
  }
})().catch(e=>{console.error(e);process.exitCode=1});
'''
    result = subprocess.run(['node', '-e', js], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
