"""GoodWe presets must not invent modes missing from HA's select options (#181)."""
from unittest.mock import patch

import pytest
import yaml

from discovery import discover_house
from house_config import build_battery_driver
from test_battery_presets_2026_11_05 import E
from test_solax_modbus_battery import _builder


def battery(options):
    mode = E('select.goodwe_mode', 'Inverter operation mode', m='GoodWe', st='general')
    if options is not None:
        mode['options'] = options
    return discover_house([
        E('sensor.goodwe_soc', 'Battery State of Charge', m='GoodWe', dc='battery', u='%'),
        E('sensor.goodwe_power', 'Battery Power', m='GoodWe', dc='power', u='W'), mode])['battery']


@pytest.mark.parametrize('options, expected', [
    (['general', 'eco_charge', 'eco_discharge'], {'auto': 'general', 'charge': 'eco_charge', 'discharge': 'eco_discharge'}),
    (['general', 'eco_charge'], {'auto': 'general', 'charge': 'eco_charge'}),
    (['general', 'eco_discharge'], {'auto': 'general', 'discharge': 'eco_discharge'}),
    (['general', 'backup', 'eco', 'peak_shaving'], {'auto': 'general'}),
    ([], {}), (None, {}), ('general,eco_charge', {}),
    (['eco_charge', 'eco_discharge'], {}),
])
def test_goodwe_suggests_only_advertised_modes_with_return_to_auto(options, expected):
    result = battery(options)
    assert result['generic_suggestion']['modes'] == expected
    assert result['control_preset'] == 'goodwe'
    assert result['generic_suggestion']['entities']['mode_select'] == 'select.goodwe_mode'


def test_missing_charge_mode_never_becomes_a_driver_command():
    result = battery(['general', 'backup', 'eco'])
    cfg = yaml.safe_load(_builder()({'battery': result}))
    driver = build_battery_driver(cfg)
    assert driver.supported_intents() == {'auto'}
    with patch('drivers.battery_generic.homeassistant') as ha:
        assert driver.apply_intent('charge', 3000) is False
        ha.set_select.assert_not_called()
        ha.set_number.assert_not_called()


def test_missing_options_remain_read_only():
    cfg = yaml.safe_load(_builder()({'battery': battery(None)}))
    driver = build_battery_driver(cfg)
    assert driver.supported_intents() == set()
    with patch('drivers.battery_generic.homeassistant') as ha:
        assert driver.apply_intent('charge', 3000) is False
        ha.set_select.assert_not_called()
