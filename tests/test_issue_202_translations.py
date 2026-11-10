"""Deliver translated notifications without changing categories, IDs or saved source text (#202)."""
from copy import deepcopy

import pytest

import i18n_py
import notifier
import notify_log
import notify_prefs


@pytest.fixture
def delivered(monkeypatch):
    payloads, history = [], []
    monkeypatch.setattr(i18n_py, 'language', lambda: 'en')
    monkeypatch.setattr(notifier, '_init', lambda: None)
    monkeypatch.setattr(notifier, '_ha_base', 'http://test.invalid/api')
    monkeypatch.setattr(notifier, '_ha_headers', {})
    monkeypatch.setattr(notifier, 'recipients', lambda: ['mobile_app_test'])
    monkeypatch.setattr(notify_prefs, 'disabled', lambda: set())
    monkeypatch.setattr(notify_log, 'add', lambda *args, **kw: history.append(args))

    class Ok:
        def raise_for_status(self):
            pass

    def post(url, **kwargs):
        payloads.append((url, kwargs['json']))
        return Ok()

    monkeypatch.setattr(notifier.requests, 'post', post)
    return payloads, history


def test_morning_price_push_is_english_and_uses_feed_currency(delivered, monkeypatch):
    import nordpool
    monkeypatch.setattr(nordpool, 'cost_settings', lambda: {'symbol': '€'})
    payloads, history = delivered
    notifier.morning_price_tip([0.28]*24 + [0.50]*64 + [0.29]*8, 8, 1)
    payload = payloads[-1][1]
    assert payload['title'] == '⚡ Electricity tips for Tuesday'
    assert payload['message'].startswith('Good times to run the dishwasher or washing machine:\n')
    assert '00:00–06:00 (0.28 €/kWh)' in payload['message']
    assert '22:00–24:00 (0.29 €/kWh)' in payload['message']
    assert history[-1][0] == '⚡ Eltips tisdag'  # classification/history uses original source
    assert notify_prefs.category_for(history[-1][0]) == 'pris'


def test_disabled_category_is_checked_before_translation(delivered, monkeypatch):
    payloads, history = delivered
    monkeypatch.setattr(notify_prefs, 'disabled', lambda: {'pris'})
    assert notifier.send_emil('⚡ Eltips tisdag', 'Bra tider att köra disk eller tvätt:') is False
    assert payloads == [] and history[-1][2] == 'muted'


def test_swedish_notification_keeps_original_payload(delivered, monkeypatch):
    payloads, _ = delivered
    monkeypatch.setattr(i18n_py, 'language', lambda: 'sv')
    notifier.notify_spa_ready(38.5)
    assert payloads[-1][1] == {'title': '🛁 Spabadet är redo!', 'message': 'Temperaturen är nu 38.5 °C.'}


def test_action_ids_and_original_data_are_preserved(delivered):
    payloads, _ = delivered
    data = {'tag': 'pris_elbil_42', 'actions': [{'action': 'STARTA_BIL', 'title': 'Spara och starta'}],
            'url': '/sv/inställningar', 'nested': {'text': 'Spara'}}
    original = deepcopy(data)
    assert notifier.send_emil('🚗 Bilen laddar', 'Laddningen av Laddaren 42 har startat med 7.2 kW.', data)
    result = payloads[-1][1]
    assert 'Laddaren 42' in result['message'] and 'Charging' in result['message']
    assert result['data']['actions'][0] == {'action': 'STARTA_BIL', 'title': 'Save and start'}
    assert result['data']['tag'] == data['tag'] and result['data']['nested'] == data['nested']
    assert result['data']['url'] == data['url'] and data == original


def test_script_routing_and_multiline_messages(delivered):
    payloads, _ = delivered
    assert notifier._send('script.test_alert', '🛁 Spabadet är redo!', 'Temperaturen är nu 38.5 °C.\nKontrollera anslutningen.')
    assert payloads[-1][0].endswith('/services/script/test_alert')
    assert payloads[-1][1]['message'] == 'The temperature is now 38.5 °C.\nCheck the connection.'


def test_translation_failure_does_not_drop_alert(delivered, monkeypatch):
    def broken():
        raise RuntimeError('test dictionary failure')
    monkeypatch.setattr(i18n_py, 'language', broken)
    payloads, _ = delivered
    assert notifier._send('mobile_app_test', 'Värmepumplarm!', 'Kontrollera värmepumpen.')
    assert payloads[-1][1] == {'title': 'Värmepumplarm!', 'message': 'Kontrollera värmepumpen.'}


@pytest.mark.parametrize('source, expected', [
    ('Priskällan sparad - priserna hämtas om inom en minut', 'Price source saved - prices will be fetched again within a minute'),
    ('Använd effektsensorn sensor.p1_zendure_api', 'Use power sensor sensor.p1_zendure_api'),
    ('Smartmätare: sensor.p1_zendure_api (okänt märke)', 'Smart meter: sensor.p1_zendure_api (unknown brand)'),
    ('hittades (Zendure) - ingen drivrutin än, bidra gärna', 'found (Zendure) - no driver yet; contributions welcome'),
    ('Effekt: sensor.goodwe_dns_house_consumption', 'Power: sensor.goodwe_dns_house_consumption'),
    ('1 prissensor hittades i Home Assistant.', '1 price sensor found in Home Assistant.'),
    ('3 prissensorer hittades i Home Assistant.', '3 price sensors found in Home Assistant.'),
])
def test_settings_strings_preserve_entity_ids(source, expected):
    assert i18n_py.tr(source, 'en') == expected
    assert i18n_py.tr(source, 'sv') == source


@pytest.mark.parametrize('name, args, expected', [
    ('alert_high_price', (3.0, 2.5), 'The price is now 3.000 kr/kWh (>2.50 kr). Avoid high-power appliances!'),
    ('alert_low_price', (-0.2,), 'The price is now -0.200 kr/kWh – a good time to run energy-intensive appliances!'),
    ('alert_pump_alarm', (42,), 'Alarm code: 42. Check the heat pump.'),
    ('alert_spa_cover', (1.0, 0.2), 'The temperature dropped 1.0 °C in the last hour (expected about 0.2 °C/h at this outdoor temperature). Was the cover left open?'),
    ('alert_indoor_cold', (16.5, 18.0), 'The indoor temperature has fallen to 16.5°C (below 18°C).'),
    ('alert_price_fallback', (), "Could not fetch today's electricity prices (elprisetjustnu.se may be unavailable). The system is using yesterday's price profile as an approximation until actual prices are available again."),
])
def test_operational_alerts_delivered_in_english(delivered, name, args, expected):
    payloads, _ = delivered
    getattr(notifier, name)(*args)
    assert payloads[-1][1]['message'] == expected
