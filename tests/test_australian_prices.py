"""Australia/AUD and mutable HA prices (#212/#207), against a real isolated PostgreSQL schema."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

import ew_settings
import nordpool

UTC = timezone.utc
SYDNEY = ZoneInfo('Australia/Sydney')
NOW = datetime(2026, 11, 10, 0, 5, tzinfo=UTC)


class Clock(datetime):
    instant = NOW

    @classmethod
    def now(cls, tz=None):
        return cls.instant.astimezone(tz) if tz else cls.instant.replace(tzinfo=None)


@pytest.fixture
def prices(db, monkeypatch, tmp_path):
    schema = 'au_prices_' + uuid4().hex
    db.execute(f'CREATE SCHEMA {schema}')
    db.execute(f'SET search_path TO {schema}')

    @contextmanager
    def get_db():
        yield db

    monkeypatch.setattr(nordpool, 'get_db', get_db)
    monkeypatch.setattr(nordpool, 'datetime', Clock)
    monkeypatch.setattr(Clock, 'instant', NOW)
    monkeypatch.setattr(nordpool, '_ha_refresh_state', {})
    monkeypatch.setattr(ew_settings, 'PATH', str(tmp_path / 'settings.json'))
    ew_settings._cache.update(mtime=None, data={})
    for key in ('PRICE_COUNTRY', 'PRICE_CURRENCY', 'PRICE_SOURCE', 'PRICE_AREA', 'PRICE_TIMEZONE',
                'PRICE_FINAL', 'PRICE_CURRENT_ENTITY', 'PRICE_INCLUDES_VAT'):
        monkeypatch.delenv(key, raising=False)
    ew_settings.update(price_country='AU', price_ha_entity='sensor.amber_general_forecast')
    nordpool.init_db()
    try:
        yield db
    finally:
        db.execute('SET search_path TO public')
        db.execute(f'DROP SCHEMA {schema} CASCADE')


def forecast(start, value, minutes=5):
    return {'start_time': (start + timedelta(seconds=1)).isoformat(),
            'end_time': (start + timedelta(minutes=minutes)).isoformat(), 'per_kwh': value}


def response(data, status=200):
    r = Mock(status_code=status)
    r.json.return_value = data
    return r


def feed(monkeypatch, forecasts, actual=0.22, actual_start=NOW):
    calls = []

    def get(url, **kwargs):
        calls.append(url)
        if url.endswith('_forecast'):
            return response({'state': '999', 'attributes': {'unit_of_measurement': 'AUD/kWh', 'forecasts': forecasts}})
        return response({'state': actual, 'attributes': {'unit_of_measurement': 'AUD/kWh',
                        'start_time': (actual_start + timedelta(seconds=1)).isoformat(),
                        'end_time': (actual_start + timedelta(minutes=5)).isoformat()}})

    monkeypatch.setattr(nordpool.requests, 'get', get)
    return calls


def test_au_defaults_and_tax(prices):
    c = nordpool.cost_settings()
    assert (c['country'], c['currency'], c['symbol'], c['vat_pct']) == ('AU', 'AUD', 'A$', 10)
    assert c['buy_extra'] == c['sell_extra'] == 0
    assert c['timezone'] == 'Australia/Sydney'
    assert nordpool.price_source() == 'ha_nordpool'
    assert nordpool.full_buy_cost(0.33) == pytest.approx(0.33)  # HA already includes GST
    assert nordpool.full_sell_income(0.33) == pytest.approx(0.30)
    ew_settings.update(price_includes_vat=False)
    assert nordpool.full_buy_cost(0.30) == pytest.approx(0.33)
    assert eval(nordpool.sql_buy_cost_expr('0.30')) == pytest.approx(0.33)


def test_mutable_prices_preserve_completed_history_and_store_actual(prices, monkeypatch):
    past, future = NOW - timedelta(minutes=5), NOW + timedelta(minutes=5)
    prices.execute('INSERT INTO elpriser VALUES (%s, %s, %s)', (past, NOW, 0.10))
    rows = [forecast(past, 4.0), forecast(NOW, 0.30), forecast(future, 0.40)]
    feed(monkeypatch, rows)
    assert nordpool.fetch_ha_nordpool_and_save(NOW.astimezone(SYDNEY))
    assert nordpool.get_price_at(past) == pytest.approx(0.10)
    assert nordpool.get_price_at(NOW) == pytest.approx(0.22)  # actual, not forecast sensor state 999
    assert nordpool.get_price_at(future) == pytest.approx(0.40)
    rows[-1]['per_kwh'] = 0.60
    assert nordpool.fetch_ha_nordpool_and_save(NOW.astimezone(SYDNEY))
    assert nordpool.get_price_at(future) == pytest.approx(0.60)
    assert nordpool.get_price_at(past) == pytest.approx(0.10)
    assert prices.execute('SELECT count(*) FROM elpriser').fetchone()[0] == 3


def test_day_filter_uses_sydney_not_stockholm(prices, monkeypatch):
    # 00:10 Sydney on Nov 11 is still Nov 10 in Sweden.
    start = datetime(2026, 11, 11, 0, 10, tzinfo=SYDNEY)
    feed(monkeypatch, [forecast(start, 0.31)], actual='unavailable')
    assert nordpool.fetch_ha_nordpool_and_save(start.replace(hour=0, minute=0))
    assert nordpool.get_price_at(start) == pytest.approx(0.31)


def test_refresh_runs_with_existing_rows_before_publication_gate(prices, monkeypatch):
    tick = [1000.0]
    monkeypatch.setattr(nordpool.time, 'monotonic', lambda: tick[0])
    future = NOW + timedelta(days=1)
    rows = [forecast(NOW, 0.30), forecast(future, 0.40)]
    calls = feed(monkeypatch, rows)
    nordpool.ensure_prices_exist()  # 11:05 Sydney: no 13:30 gate for dynamic feeds
    assert nordpool.get_price_at(future) == pytest.approx(0.40)
    count = len(calls)
    rows[-1]['per_kwh'] = 0.70
    nordpool.ensure_prices_exist()
    assert len(calls) == count
    tick[0] += 300
    nordpool.ensure_prices_exist()
    assert len(calls) > count
    assert nordpool.get_price_at(future) == pytest.approx(0.70)


def test_restart_probes_dynamic_sensor_even_with_cached_database(prices, monkeypatch):
    future = NOW + timedelta(minutes=5)
    prices.execute('INSERT INTO elpriser VALUES (%s, %s, %s)', (future, future + timedelta(minutes=5), 0.10))
    feed(monkeypatch, [forecast(future, 0.60)], actual='unknown')
    nordpool.ensure_prices_exist()
    assert nordpool.get_price_at(future) == pytest.approx(0.60)


def test_fixed_feed_never_overwrites_published_prices(prices, monkeypatch):
    ew_settings.update(price_final='true')
    rows = [forecast(NOW, 0.30)]
    calls = feed(monkeypatch, rows)
    nordpool.ensure_prices_exist()
    count = len(calls)
    rows[0]['per_kwh'] = 0.90
    assert nordpool.fetch_ha_nordpool_and_save(NOW.astimezone(SYDNEY))
    assert nordpool.get_price_at(NOW) == pytest.approx(0.30)
    assert all(not x.endswith('_price') for x in calls)
    count = len(calls)
    nordpool.ensure_prices_exist()
    assert len(calls) == count  # existing day-ahead rows do not cause periodic refreshes


def test_explicit_refresh_for_non_amber_source(prices, monkeypatch):
    ew_settings.update(price_final='false', price_ha_entity='sensor.custom_prices')
    rows = [{'start': NOW.isoformat(), 'end': (NOW + timedelta(minutes=30)).isoformat(), 'value': 0.20}]
    monkeypatch.setattr(nordpool.requests, 'get', lambda *a, **k: response({'attributes': {'rates': rows}}))
    assert nordpool.fetch_ha_nordpool_and_save(NOW.astimezone(SYDNEY))
    rows[0]['value'] = 0.50
    assert nordpool.fetch_ha_nordpool_and_save(NOW.astimezone(SYDNEY))
    assert nordpool.get_price_at(NOW) == pytest.approx(0.50)


def test_stale_actual_sensor_is_not_used(prices, monkeypatch):
    feed(monkeypatch, [forecast(NOW, 0.30)], actual=4.0, actual_start=NOW - timedelta(minutes=10))
    assert nordpool.fetch_ha_nordpool_and_save(NOW.astimezone(SYDNEY))
    assert nordpool.get_price_at(NOW) == pytest.approx(0.30)


def test_slot_finalizes_when_completed(prices, monkeypatch):
    rows = [forecast(NOW, 0.30), forecast(NOW + timedelta(minutes=5), 0.40)]
    feed(monkeypatch, rows)
    assert nordpool.fetch_ha_nordpool_and_save(NOW.astimezone(SYDNEY))
    monkeypatch.setattr(Clock, 'instant', NOW + timedelta(minutes=5))
    rows[0]['per_kwh'] = 7.0
    assert nordpool.fetch_ha_nordpool_and_save(NOW.astimezone(SYDNEY))
    assert nordpool.get_price_at(NOW) == pytest.approx(0.22)


def test_selected_timezone_controls_tariff_sql_and_naive_timestamps(prices):
    ew_settings.update(price_timezone='Australia/Adelaide', price_tou_extra=0.5,
                       price_tou_hours='7-9', price_tou_months='1-12', price_tou_weekdays=False)
    instant = datetime(2026, 11, 10, 7, 30, tzinfo=ZoneInfo('Australia/Adelaide'))
    assert nordpool.tou_extra_at(instant.astimezone(UTC)) == 0.5
    assert 'Australia/Adelaide' in nordpool.sql_buy_cost_expr('spot', 't')
    assert nordpool._parse_ts('2026-11-10T07:30:00').utcoffset() == timedelta(hours=10, minutes=30)


def test_five_minute_prices_become_weighted_quarters():
    start = NOW.replace(minute=0)
    rows = [(start + timedelta(minutes=i*5), start + timedelta(minutes=(i+1)*5), p)
            for i, p in enumerate([0.10, 0.20, 0.60, 0.90, 0.90, 0.90])]
    assert nordpool.quarter_price_profile(rows, start, start + timedelta(minutes=30)) == pytest.approx([0.30, 0.90])


@pytest.mark.parametrize('day, count', [(datetime(2026, 4, 5, tzinfo=SYDNEY), 100),
                                       (datetime(2026, 10, 4, tzinfo=SYDNEY), 92)])
def test_australian_dst_day_has_correct_quarter_count(day, count):
    end = day + timedelta(days=1)
    assert len(nordpool.quarter_price_profile([(day, end, 0.30)], day, end)) == count


def test_legacy_one_second_forecasts_are_replaced_without_overlap(prices, monkeypatch):
    prices.execute('INSERT INTO elpriser VALUES (%s, %s, %s)',
                   (NOW + timedelta(seconds=1), NOW + timedelta(minutes=5), 9.0))
    feed(monkeypatch, [forecast(NOW, 0.30)])
    assert nordpool.fetch_ha_nordpool_and_save(NOW.astimezone(SYDNEY))
    assert nordpool.get_price_at(NOW) == pytest.approx(0.22)
    assert nordpool.get_price_at(NOW + timedelta(seconds=2)) == pytest.approx(0.22)
    assert prices.execute('SELECT count(*) FROM elpriser').fetchone()[0] == 1


def test_current_price_override_for_renamed_sensor(prices, monkeypatch):
    ew_settings.update(price_current_entity='sensor.actual_import')
    replies = {'sensor.amber_general_forecast': {'attributes': {'forecasts': [forecast(NOW, 0.30)]}},
               'sensor.actual_import': {'state': '18', 'attributes': {'unit_of_measurement': 'c/kWh',
                                        'start_time': NOW.isoformat(), 'end_time': (NOW + timedelta(minutes=5)).isoformat()}}}
    monkeypatch.setattr(nordpool.requests, 'get', lambda url, **kw: response(replies[url.rsplit('/', 1)[-1]]))
    assert nordpool.fetch_ha_nordpool_and_save(NOW.astimezone(SYDNEY))
    assert nordpool.get_price_at(NOW) == pytest.approx(0.18)


def test_failed_refresh_retains_prices_and_retries(prices, monkeypatch):
    rows = [forecast(NOW, 0.30)]
    feed(monkeypatch, rows)
    nordpool.ensure_prices_exist()
    monkeypatch.setattr(nordpool.time, 'monotonic', lambda: 10**12)
    monkeypatch.setattr(nordpool.requests, 'get', lambda *args, **kw: response({}, 503))
    nordpool.ensure_prices_exist()
    assert nordpool.get_price_at(NOW) == pytest.approx(0.22)
    calls = feed(monkeypatch, rows, actual=0.25)
    nordpool.ensure_prices_exist()
    assert calls and nordpool.get_price_at(NOW) == pytest.approx(0.25)


def test_price_info_returns_quarters_for_five_minute_feed(prices, monkeypatch):
    start = NOW.replace(minute=0)
    rows = [forecast(start + timedelta(minutes=5*i), 0.30) for i in range(9)]
    feed(monkeypatch, rows, actual=0.30)
    current, _, _, profile = nordpool.get_price_info()
    assert current == pytest.approx(0.30)
    assert len(profile) == 96 and profile == pytest.approx([0.30]*96)


def test_source_change_preserves_completed_rows(prices, monkeypatch):
    past = NOW - timedelta(minutes=5)
    prices.execute('INSERT INTO elpriser VALUES (%s, %s, %s)', (past, NOW, 0.12))
    ew_settings.update(price_fetched_for='old source')
    feed(monkeypatch, [forecast(NOW, 0.30)])
    nordpool.ensure_prices_exist()
    assert nordpool.get_price_at(past) == pytest.approx(0.12)


def test_price_settings_api_persists_timezone_and_source_options(prices, monkeypatch):
    import asyncio
    import sys
    from test_solax_modbus_battery import _builder
    _builder()
    app = sys.modules['webdashboard_app']
    monkeypatch.setattr(app.AUTH, 'session', lambda request: ('owner', 'test'))

    def req(data):
        async def json_body():
            return data
        return Mock(json=json_body)

    result = asyncio.run(app.price_settings_set(req({'country': 'AU', 'timezone': 'Australia/Brisbane'})))
    assert result == {'ok': True}
    assert ew_settings.get('price_timezone') == 'Australia/Brisbane'
    result = asyncio.run(app.price_settings_get())
    assert result['symbol'] == 'A$' and result['countries']['AU']['symbol'] == 'A$'
    assert result['timezone'] == 'Australia/Brisbane'
    result = asyncio.run(app.price_source_set(req({'ha_entity': 'sensor.amber_general_forecast', 'final': 'false',
                                                  'current_entity': 'sensor.actual_import', 'includes_vat': True})))
    assert result == {'ok': True}
    assert nordpool.price_final_mode() == 'false'
    assert ew_settings.get('price_current_entity') == 'sensor.actual_import'
    result = asyncio.run(app.price_settings_set(req({'country': 'AU', 'timezone': 'invalid/zone'})))
    assert result.status_code == 400
    assert ew_settings.get('price_timezone') == 'Australia/Brisbane'
    result = asyncio.run(app.price_source_set(req({'ha_entity': 'sensor.x', 'final': 'invalid'})))
    assert result.status_code == 400
    result = asyncio.run(app.price_source_set(req({'ha_entity': 'sensor.x', 'current_entity': 'not a sensor'})))
    assert result.status_code == 400


def test_au_never_uses_swedish_api(prices, monkeypatch):
    def unexpected_request(*args, **kwargs):
        pytest.fail('Australian installations must not import Swedish prices')
    monkeypatch.setattr(nordpool.requests, 'get', unexpected_request)
    assert nordpool.fetch_api_and_save(NOW) is False


def test_missing_current_interval_remains_unknown(prices, monkeypatch):
    feed(monkeypatch, [forecast(NOW + timedelta(minutes=5), 0.30)], actual='unavailable')
    assert nordpool.fetch_ha_nordpool_and_save(NOW.astimezone(SYDNEY))
    assert nordpool.get_price_at(NOW) is None


def test_actual_with_different_interval_does_not_create_overlapping_rows(prices, monkeypatch):
    feed(monkeypatch, [forecast(NOW - timedelta(minutes=5), 0.30, minutes=30)], actual=0.22)
    assert nordpool.fetch_ha_nordpool_and_save(NOW.astimezone(SYDNEY))
    assert nordpool.get_price_at(NOW) == pytest.approx(0.22)
    assert prices.execute('SELECT count(*) FROM elpriser').fetchone()[0] == 1


def test_changing_refresh_mode_does_not_erase_existing_prices_on_failure(prices, monkeypatch):
    feed(monkeypatch, [forecast(NOW, 0.30)])
    nordpool.ensure_prices_exist()
    ew_settings.update(price_final='false')
    monkeypatch.setattr(nordpool.requests, 'get', lambda *a, **k: response({}, 503))
    nordpool.ensure_prices_exist()
    assert nordpool.get_price_at(NOW) == pytest.approx(0.22)
