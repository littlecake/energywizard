"""Catalog parity and price text must preserve amounts and the selected currency."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import i18n_py
import plan_brief

ROOT = Path(__file__).resolve().parents[1]


def test_catalogs_cover_english_and_preserve_placeholders():
    en = json.loads((ROOT / 'smartbox/i18n/en.json').read_text(encoding='utf-8'))
    cs = json.loads((ROOT / 'smartbox/i18n/cs.json').read_text(encoding='utf-8'))
    assert set(en) <= set(cs)
    for catalog in (en, cs):
        for key, value in catalog.items():
            if key.startswith('_') or not isinstance(value, str) or not value:
                continue
            assert key.count('#') == value.count('#'), key
            assert set(re.findall(r'\{[a-zA-Z][a-zA-Z0-9_]*\}', key)) == set(re.findall(r'\{[a-zA-Z][a-zA-Z0-9_]*\}', value)), key


@pytest.mark.parametrize('source,expected', [
    ('Priset är nu 3.000 Kč/kWh (>2.50 Kč). Undvik tunga maskiner!', 'Cena je nyní 3.000 Kč/kWh (>2.50 Kč). Nepoužívejte energeticky náročné spotřebiče!'),
    ('Elpriset är 2.50 Kč/kWh (billigt).', 'Cena elektřiny je 2.50 Kč/kWh (levná).'),
    ('Använd effektsensorn sensor.solax_pv_power_1', 'Použít senzor výkonu sensor.solax_pv_power_1'),
    ('Laddningen av Auto 1 har startat med 7.2 kW.', 'Nabíjení Auto 1 začalo výkonem 7.2 kW.'),
    ('EnergyWizard har sparat 3.2 Kč idag jämfört med ett vanligt hushåll utan styrning (inkl. moms).', 'EnergyWizard dnes ušetřil 3.2 Kč oproti běžné domácnosti bez řízení (včetně DPH).'),
    ('Grundläge: Billig el (1.00 Kč inkl. tidstariff 0.10 <= 2.00 Kč). Värmepump och Varmvatten i normaldrift.', 'Základní režim: levná elektřina (1.00 Kč včetně časového tarifu 0.10 <= 2.00 Kč). Tepelné čerpadlo a teplá voda v běžném režimu.'),
])
def test_czech_dynamic_messages(source, expected):
    assert i18n_py.tr(source, 'cs') == expected
    assert i18n_py.tr(source, 'sv') == source


def test_plan_prices_use_selected_currency():
    assert plan_brief._kr(.31) == '31 öre'
    assert plan_brief._kr(.31, 'CZK', 'Kč') == '0,31 Kč'
    assert plan_brief._kr(.31, 'AUD', 'A$') == '0,31 A$'


@pytest.mark.skipif(shutil.which('node') is None, reason='Node.js required')
def test_browser_translations_and_charging_cost_currency():
    js = r'''
const fs = require('fs'), vm = require('vm'), assert = require('assert');
const dict = JSON.parse(fs.readFileSync('smartbox/i18n/cs.json', 'utf8'));
const ctx = vm.createContext({console, document:{readyState:'loading',currentScript:null,documentElement:{},addEventListener(){}},
  localStorage:{getItem:()=> 'cs'}, navigator:{}, location:{},
  fetch:async url=>({ok:true,json:async()=>url.endsWith('config')?{default:'cs',languages:{sv:'Svenska',en:'English',cs:'Čeština'}}:dict})});
ctx.window=ctx;
vm.runInContext(fs.readFileSync('smartbox/i18n/i18n.js','utf8'),ctx);
(async()=>{
 await ctx.I18N.ready;
 assert.equal(ctx.I18N.tr('Elpriset är 2.50 Kč/kWh (billigt).'), 'Cena elektřiny je 2.50 Kč/kWh (levná).');
 assert.equal(ctx.I18N.tr('Priset är nu 3.000 Kč/kWh (>2.50 Kč). Undvik tunga maskiner!'), 'Cena je nyní 3.000 Kč/kWh (>2.50 Kč). Nepoužívejte energeticky náročné spotřebiče!');
 vm.runInContext(fs.readFileSync('smartbox/static/journal.js','utf8'),ctx);
 const element=()=>({style:{},setAttribute(){},addEventListener(){},getBoundingClientRect(){return {left:0,width:480}},innerHTML:''});
 const nodes={svg:element(),'.sun':element(),'.cur':element(),'.g':element()};
 const root={innerHTML:'',querySelector(k){return nodes[k]},querySelectorAll(){return []}};
 ctx.document.createElement=()=>element(); ctx.document.head={appendChild(){}};
 vm.runInContext(fs.readFileSync('smartbox/static/planskyline.js','utf8'),ctx);
 const t='2026-11-10T12:00:00+01:00';
 ctx.EWPlanView.skyline(root,{slots:[{t,price:2.5,sun_w:0,ev:{},bat:'charge',soc:50},{t:'2026-11-10T12:15:00+01:00',price:3,sun_w:0,ev:{}}],cars:[]},{lang:'cs',unit:'Kč'});
 assert.match(nodes['.g'].innerHTML,/2,50 Kč\/kWh/);
 assert.match(nodes['.g'].innerHTML,/Nabíjení/);
 assert.match(root.innerHTML,/Vysoká budova = drahá elektřina/);
 const row={kr:27,kwh:1,solar_kwh:0}, d={periods:{today:row,week:row,month:row}};
 assert.match(ctx.EWJournal.evCostHtml(d,{unit:'Kč'}), /27 Kč/);
 assert.match(ctx.EWJournal.evCostHtml(d,{unit:'A$'}), /27 A\$/);
 assert.match(ctx.EWJournal.evCostHtml(d), /27 kr/);
})().catch(e=>{console.error(e);process.exitCode=1});
'''
    result = subprocess.run(['node', '-e', js], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_price_alerts_and_battery_reason_use_contract_currency(monkeypatch):
    import battery_control
    import nordpool
    import notifier
    sent = []
    monkeypatch.setattr(nordpool, 'cost_settings', lambda: {'symbol': 'Kč'})
    monkeypatch.setattr(notifier, 'send_emil', lambda title, msg: sent.append((title, msg)))
    notifier.alert_high_price(3, 2.5)
    assert '3.000 Kč/kWh (>2.50 Kč)' in sent[-1][1]
    assert i18n_py.tr(sent[-1][1], 'cs').startswith('Cena je nyní 3.000 Kč/kWh')
    notifier.alert_low_price(-.2)
    assert '-0.200 Kč/kWh' in sent[-1][1]
    result = battery_control.decide({'soc': 50, 'price': -.2, 'currency_symbol': 'Kč'},
                                    {'control': 'styr'}, {'auto', 'charge'})
    assert '-0.20 Kč/kWh' in result['reason']
    assert i18n_py.tr(result['reason'], 'cs').startswith('Záporná cena (-0.20 Kč/kWh)')
