"""Skoda EVs must not become stationary battery suggestions (#225)."""
import pytest
import yaml

from discovery import discover_house
from test_solax_modbus_battery import _builder


def skoda(maker='Škoda Auto', model='Enyaq'):
    # Official HA integration: manufacturer="Škoda Auto". No tracker is required.
    # Entity IDs match the user's report; the device name is user-configurable.
    head = {'a': 'Garage', 'd': 'dev_enyaq', 'dn': 'Garage Enyaq', 'm': maker, 'mo': model}
    return [
        {**head, 'e': 'sensor.garage_enyaq_battery_state_of_charge',
         'n': 'Garage Enyaq Battery state of charge', 'dc': 'battery', 'u': '%', 'st': '62'},
        {**head, 'e': 'sensor.garage_enyaq_charging_power',
         'n': 'Garage Enyaq Charging power', 'dc': 'power', 'u': 'kW', 'st': '7.2'},
    ]


@pytest.mark.parametrize('maker, model', [
    ('Škoda Auto', 'Enyaq'), ('ŠKODA AUTO', 'Enyaq'),
    ('Skoda', 'Enyaq'), ('skoda auto', 'Enyaq'), ('', 'Škoda Enyaq'),
])
def test_skoda_without_tracker_is_a_car(maker, model):
    result = discover_house(skoda(maker, model))
    assert len(result['cars']) == 1
    car = result['cars'][0]
    assert car['driver'] == 'generic_ev' and car['driver_known']
    assert car['soc_entity'] == 'sensor.garage_enyaq_battery_state_of_charge'
    assert result['battery'] is None


@pytest.mark.parametrize('maker, model', [('BYD', 'Battery-Box Premium HVS'), ('Tesla', 'Powerwall 2')])
def test_skoda_and_stationary_battery_are_kept_separate(maker, model):
    head = {'a': 'Garage', 'd': 'dev_home_battery', 'dn': model, 'm': maker, 'mo': model}
    home_battery = [
        {**head, 'e': 'sensor.home_battery_soc', 'n': 'Battery SOC', 'dc': 'battery', 'u': '%', 'st': '70'},
        {**head, 'e': 'sensor.home_battery_power', 'n': 'Battery Power', 'dc': 'power', 'u': 'W', 'st': '500'},
    ]
    for entities in (skoda() + home_battery, home_battery + skoda()):
        result = discover_house(entities)
        assert len(result['cars']) == 1
        assert result['cars'][0]['soc_entity'] == 'sensor.garage_enyaq_battery_state_of_charge'
        assert result['battery']['soc_entity'] == 'sensor.home_battery_soc'
        assert result['battery']['power_entity'] == 'sensor.home_battery_power'


def test_generated_yaml_places_skoda_in_evs():
    cfg = yaml.safe_load(_builder()(discover_house(skoda())))
    assert len(cfg['evs']) == 1
    assert cfg['evs'][0]['driver'] == 'generic_ev'
    assert cfg['evs'][0]['entities']['soc'] == 'sensor.garage_enyaq_battery_state_of_charge'
    assert not cfg.get('battery', {}).get('enabled')
