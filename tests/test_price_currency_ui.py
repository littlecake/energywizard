"""Exercise currency labels through the actual desktop/mobile rendering functions."""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.skipif(shutil.which('node') is None, reason='Node.js required for frontend rendering checks')
def test_aud_and_sek_rendering():
    js = r'''
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const element = { style: { setProperty() {} }, classList: { add() {}, remove() {} },
  setAttribute() {}, removeAttribute() {}, addEventListener() {} };
function context() {
  return vm.createContext({ document: { documentElement: element, getElementById: () => element,
    querySelector: () => element, addEventListener() {} },
    window: { addEventListener() {}, matchMedia: () => ({ matches: true }) }, localStorage: { getItem() { return null; } },
    navigator: {}, location: { search: '' }, URLSearchParams, history: { replaceState() {} },
    matchMedia: () => ({ matches: false }), innerWidth: 400, innerHeight: 800,
    setInterval() {}, setTimeout() {}, clearTimeout() {}, console });
}
const desktop = context();
vm.runInContext(fs.readFileSync('webdashboard/static/app.js', 'utf8').replace(/\nboot\(\);\s*$/, ''), desktop);
assert.equal(vm.runInContext('fmtKrOre(0.31)', desktop), '31 öre');
vm.runInContext('moneyCurrency="AUD"; moneySymbol="A$";', desktop);
assert.equal(vm.runInContext('fmtKrOre(0.31)', desktop), '0.31 A$');
assert.equal(vm.runInContext('fmtKrOre(-0.10)', desktop), '-0.10 A$');
assert.match(vm.runInContext('savingsCardHtml({periods:{week:{saved_kr:5,paid_kr:10,kwh:50,days:1}}})', desktop), /5 A\$/);
const mobile = context();
vm.runInContext(fs.readFileSync('ewapp/static/app.js', 'utf8').replace(/\nstart\(\);\s*$/, ''), mobile);
vm.runInContext('S={currency_symbol:"A$"};', mobile);
assert.match(vm.runInContext('planChart({now:0.31,hours:[]}, [])', mobile), /A\$\/kWh/);
vm.runInContext('S={currency_symbol:"kr"};', mobile);
assert.match(vm.runInContext('planChart({now:0.31,hours:[]}, [])', mobile), /kr\/kWh/);
'''
    result = subprocess.run(['node', '-e', js], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
