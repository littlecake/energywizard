"""cFos Powerbrain: choose session controls, normalize status, and reuse the generic charger."""
from unittest.mock import patch

import pytest
import yaml

import discovery
from drivers.charger_generic import normalize_status
from house_config import build_charger_drivers
from test_solax_modbus_battery import _builder


def entities(maker='cFos'):
    head = {'d': 'dev_evse', 'dn': 'Garage', 'm': maker, 'mo': 'cFos Power Brain 2.1', 'a': 'Garage'}
    def e(domain, suffix, name, unit=None, dc=None, state='on'):
        return {**head, 'e': f'{domain}.garage_{suffix}', 'n': 'Garage '+name, 'u': unit, 'dc': dc, 'st': state}
    return [
        e('switch', 'charging_rules_enabled', 'Charging Rules Enabled'),
        e('switch', 'user_rules_enabled', 'User Rules Enabled'),
        e('number', 'maximum_current', 'Maximum Current', 'A'),
        e('number', 'current_limit_override', 'Current Limit Override', 'A'),
        e('switch', 'charging_enabled', 'Charging Enabled'),
        e('sensor', 'state', 'State', state='2: Car connected'),
        e('sensor', 'charging_power', 'Charging Power', 'W', 'power', '0'),
        e('sensor', 'current_l1', 'Current L1', 'A', 'current', '0'),
    ]


@pytest.fixture(autouse=True)
def no_device_fallback(monkeypatch):
    monkeypatch.setattr(discovery, '_check_configured_heat_pump', lambda: None)


@pytest.mark.parametrize('maker', ['cFos', 'CFOS', 'cFos eMobility'])
def test_cfos_discovery_selects_correct_controls_independent_of_order(maker):
    for data in (entities(maker), list(reversed(entities(maker)))):
        chargers = discovery.discover_house(data)['chargers']
        assert len(chargers) == 1
        assert chargers[0]['generic_suggestion'] == {'driver': 'generic', 'entities': {
            'switch': 'switch.garage_charging_enabled',
            'current_limit': 'number.garage_current_limit_override',
            'status': 'sensor.garage_state', 'power': 'sensor.garage_charging_power',
            'current_import': 'sensor.garage_current_l1'}}


@pytest.mark.parametrize('raw, expected', [
    ('1: Standby', 'disconnected'), ('2: Car connected', 'awaiting_start'),
    ('3: Charging', 'charging'), ('4: Charging/vent', 'charging'),
    ('5: Error', 'offline'), ('6: Offline', 'offline'),
])
def test_cfos_status_values_are_usable_by_engine(raw, expected):
    assert normalize_status(raw) == expected


@pytest.mark.parametrize('missing', ['charging_enabled', 'current_limit_override', 'state'])
def test_incomplete_cfos_contract_is_not_guessed(missing):
    data = [x for x in entities() if not x['e'].endswith('_'+missing)]
    assert discovery.discover_house(data)['chargers'] == []


def test_cfos_meter_does_not_become_charger():
    data = [x for x in entities() if x['e'].endswith('_state') or x['e'].endswith('_charging_power')]
    assert discovery.discover_house(data)['chargers'] == []


def test_milliamps_are_not_silently_treated_as_amps():
    data = entities()
    next(x for x in data if x['e'].endswith('_current_limit_override'))['u'] = 'mA'
    assert discovery.discover_house(data)['chargers'] == []


def test_generated_yaml_and_driver_use_only_session_controls():
    choice = discovery.discover_house(entities())['chargers']
    assert len(choice) == 1
    charger = {**choice[0], **choice[0]['generic_suggestion']}
    cfg = yaml.safe_load(_builder()({'cars': [{'id': 'ev', 'driver': 'generic_ev', 'charger': charger}]}))
    driver = build_charger_drivers(cfg)['ev']
    with patch('drivers.charger_generic.homeassistant') as ha:
        ha.set_number.return_value = True
        driver.turn_on()
        assert driver.set_limit_a(10)
        driver.turn_off()
        assert ha.set_switch.call_args_list[0].args == ('switch.garage_charging_enabled', True)
        assert ha.set_switch.call_args_list[1].args == ('switch.garage_charging_enabled', False)
        ha.set_number.assert_called_once_with('number.garage_current_limit_override', 10)
        ha._get_raw_state.return_value = '2: Car connected'
        ha._get_numeric_state.return_value = 0
        ha.get_power_w.return_value = 0
        ha._states_cache = {'sensor.garage_charging_power': {'attributes': {'unit_of_measurement': 'W'}}}
        state = driver.read_state()
        assert state['status'] == 'awaiting_start' and state['current_a'] == 0 and not state['current_is_limit']
        assert state['power_kw'] == 0
