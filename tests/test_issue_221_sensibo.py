"""Sensibo climate discovery and generic room-setpoint control (#221)."""
from unittest.mock import patch

import pytest
import yaml

import discovery
from house_config import build_heat_pump_driver
from test_solax_modbus_battery import _builder


def entities(domain='climate', model='Sky'):
    head = {'d': 'dev_sensibo', 'dn': 'Living room', 'm': 'Sensibo', 'mo': model, 'a': 'Living room'}
    # The official integration names the device after the room; its brand is in metadata.
    return [
        {**head, 'e': 'sensor.living_room_temperature', 'n': 'Living room temperature',
         'dc': 'temperature', 'u': '°C', 'st': '21.5'},
        {**head, 'e': domain + '.living_room', 'n': 'Living room', 'dc': None, 'u': None, 'st': 'heat'},
    ]


@pytest.fixture(autouse=True)
def no_live_fallback(monkeypatch):
    monkeypatch.setattr(discovery, '_check_configured_heat_pump', lambda: None)


@pytest.mark.parametrize('model', ['Sky', 'Air', 'Air Pro'])
def test_sensibo_climate_entity_is_discovered(model):
    pump = discovery.discover_house(entities(model=model))['heat_pump']
    assert pump is not None
    assert pump['maker'] == 'Sensibo'
    assert pump['generic_suggestion'] == {'driver': 'generic_climate', 'entities': {'climate': 'climate.living_room'}}


@pytest.mark.parametrize('domain', ['fan', 'binary_sensor'])
def test_sensibo_without_climate_is_not_a_heat_pump(domain):
    assert discovery.discover_house(entities(domain, 'Pure'))['heat_pump'] is None


def test_explicit_generic_selection_survives_yaml_and_uses_selected_climate():
    pump = discovery.discover_house(entities())['heat_pump']
    assert pump is not None
    # The wizard requires an explicit generic-control selection.
    choice = {**pump, **pump['generic_suggestion']}
    cfg = yaml.safe_load(_builder()({'heat_pump': choice}))
    driver = build_heat_pump_driver(cfg)
    with patch('drivers.heatpump_generic.homeassistant') as ha:
        ha._get_numeric_attribute.return_value = 21.5
        ha._get_raw_state.return_value = 'heat'
        assert driver.read_sensors()['indoor_temp'] == 21.5
        ha._get_numeric_attribute.assert_called_with('climate.living_room', 'current_temperature')
        ha.set_climate_temperature.return_value = True
        assert driver.set_room_temp(20.0)
        ha.set_climate_temperature.assert_called_once_with('climate.living_room', 20.0)
        assert driver.set_water_stop_temp(50.0) is False
