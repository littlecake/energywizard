"""Regression coverage for unavailable spa temperatures (#230)."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

import decisions


NOW = datetime(2026, 11, 10, 12, tzinfo=ZoneInfo('Europe/Stockholm'))


def plan(temp):
    return decisions.check_spa_schedule_plan(
        NOW, NOW + timedelta(minutes=30), temp, 38.0,
        2.0, 0.0, 0.0, 0.02, 40.0, 5.0)


@pytest.mark.parametrize('temp', [None, '', 'unavailable', float('nan'), float('inf'), -float('inf')])
def test_unavailable_water_temperature_skips_plan(smartbox, capsys, temp):
    assert plan(temp) == (False, False)
    assert 'Fel i check_spa_schedule_plan' not in capsys.readouterr().out


@pytest.mark.parametrize('temp, should_heat', [(34.0, True), ('34.0', True), (0.0, True), (40.0, False)])
def test_valid_water_temperature_still_plans(smartbox, capsys, temp, should_heat):
    assert plan(temp) == (should_heat, False)
    assert 'Fel i check_spa_schedule_plan' not in capsys.readouterr().out
