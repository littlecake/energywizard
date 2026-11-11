import pytest
import solar_mapping

CONFIG = '''# preserve this comment\nhouse_id: example\nsolar:\n  enabled: true\n  driver: generic_number\n  entities:\n    pv_power_w: sensor.old_grid # preserve note\n    today_kwh: 'sensor.old_energy'\n    export_limit_pct: number.unchanged\nbattery:\n  enabled: true\n'''


def test_only_solar_values_change():
    old = solar_mapping.inspect(CONFIG)
    new = solar_mapping.replace(CONFIG, old, {'pv_power_w': 'sensor.pv', 'today_kwh': 'sensor.pv_today'})
    assert new == CONFIG.replace('sensor.old_grid', 'sensor.pv').replace("'sensor.old_energy'", 'sensor.pv_today')
    assert solar_mapping.inspect(new) == {'pv_power_w': 'sensor.pv', 'today_kwh': 'sensor.pv_today'}


def test_stale_or_invalid_edits_are_rejected():
    expected = solar_mapping.inspect(CONFIG)
    with pytest.raises(ValueError):
        solar_mapping.replace(CONFIG, {**expected, 'pv_power_w': 'sensor.changed'}, expected)
    with pytest.raises(ValueError):
        solar_mapping.replace(CONFIG, expected, {**expected, 'pv_power_w': 'switch.invalid'})
    with pytest.raises(ValueError):
        solar_mapping.inspect(CONFIG.replace('pv_power_w: sensor.old_grid', 'pv_power_w: [sensor.old_grid]'))


def test_mapping_api_preserves_config_and_rejects_stale_update(tmp_path, monkeypatch):
    import asyncio
    from pathlib import Path
    monkeypatch.chdir(Path(__file__).resolve().parent.parent / "webdashboard")
    import webdashboard.app as app

    path = tmp_path / 'house_config.yaml'
    path.write_text(CONFIG, encoding='utf-8')
    monkeypatch.setattr(app, 'HOUSE_CONFIG_FILE', str(path))
    monkeypatch.setattr(app, '_config_writable', lambda: True)
    monkeypatch.setattr(app.AUTH, 'session', lambda request: ('owner', 'test'))
    expected = solar_mapping.inspect(CONFIG)
    selected = {'pv_power_w': 'sensor.pv', 'today_kwh': 'sensor.pv_today'}
    class Request:
        async def json(self):
            return {'expected': expected, 'entities': selected}
    result = asyncio.run(app.solar_mapping_save(Request()))
    assert result == {'ok': True}
    assert path.read_text(encoding='utf-8') == CONFIG.replace('sensor.old_grid', 'sensor.pv').replace("'sensor.old_energy'", 'sensor.pv_today')
    result = asyncio.run(app.solar_mapping_save(Request()))
    assert result.status_code == 409
    monkeypatch.setattr(app.AUTH, 'session', lambda request: ('family', 'test'))
    result = asyncio.run(app.solar_mapping_get(Request()))
    assert result.status_code == 403
