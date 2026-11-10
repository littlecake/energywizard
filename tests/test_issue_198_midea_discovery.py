"""Midea/NetHome Plus climate entities must reach the existing generic driver (#198)."""
from unittest.mock import patch

import pytest
import yaml

import discovery
from house_config import build_heat_pump_driver
from test_solax_modbus_battery import _builder


def entities(maker='Midea', domain='climate'):
    return [{'e': domain + '.living_room_ac', 'n': 'Living room', 'd': 'dev_midea', 'a': 'Living room',
             'dn': 'Living room', 'm': maker, 'mo': 'AC', 'dc': None, 'u': None, 'st': 'heat'}]


@pytest.mark.parametrize('maker', ['Midea', 'MIDEA', 'Innova'])
def test_midea_climate_is_offered_as_generic_heat_pump(monkeypatch, maker):
    monkeypatch.setattr(discovery, '_check_configured_heat_pump', lambda: None)
    pump = discovery.discover_house(entities(maker))['heat_pump']
    assert pump is not None
    assert pump['generic_suggestion'] == {'driver': 'generic_climate', 'entities': {'climate': 'climate.living_room_ac'}}


def test_midea_fan_or_temperature_sensor_is_not_assumed_to_be_a_heat_pump(monkeypatch):
    monkeypatch.setattr(discovery, '_check_configured_heat_pump', lambda: None)
    assert discovery.discover_house(entities(domain='fan'))['heat_pump'] is None
    sensor = {**entities()[0], 'e': 'sensor.fridge_temperature', 'dc': 'temperature', 'u': '°C', 'st': '4'}
    assert discovery.discover_house([sensor])['heat_pump'] is None


def test_generic_climate_choice_survives_yaml_and_controls_selected_entity(monkeypatch):
    monkeypatch.setattr(discovery, '_check_configured_heat_pump', lambda: None)
    pump = discovery.discover_house(entities())['heat_pump']
    assert pump is not None
    # Simulate the explicit "use generic control" checkbox; discovery itself does not enable control.
    chosen = {**pump, **pump['generic_suggestion']}
    cfg = yaml.safe_load(_builder()({'heat_pump': chosen}))
    driver = build_heat_pump_driver(cfg)
    with patch('drivers.heatpump_generic.homeassistant') as ha:
        ha.set_climate_temperature.return_value = True
        assert driver.set_room_temp(21.0)
        ha.set_climate_temperature.assert_called_once_with('climate.living_room_ac', 21.0)
        assert driver.set_water_stop_temp(50.0) is False
