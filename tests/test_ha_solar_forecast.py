"""Read-only Solcast adapter: units, coverage, timezone, fallback and caching."""
from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

import ha_solar_forecast as F

NOW = datetime(2026, 11, 10, 12, tzinfo=timezone.utc)


def sensor(records, **attrs):
    return {"state": "2", "last_updated": NOW.isoformat(),
            "attributes": {"unit_of_measurement": "kWh", "detailedForecast": records, **attrs}}


def record(start, kw):
    return {"period_start": start.isoformat(), "pv_estimate": kw}


class SolcastForecast(unittest.TestCase):
    def setUp(self):
        self.settings = {"solar_forecast_source": "solcast_ha", "solar_forecast_entities": ["sensor.solcast_today"]}
        p = patch.object(F.ew_settings, "get", side_effect=lambda key, default=None: self.settings.get(key, default))
        p.start()
        self.addCleanup(p.stop)
        F.invalidate()

    def test_kw_not_daily_kwh_and_hourly_energy(self):
        periods = F.parse_state(sensor([record(NOW, 2), record(NOW + timedelta(minutes=30), 4)]), NOW)
        self.assertEqual(F.average_w(periods, NOW, NOW + timedelta(hours=1)), 3000)
        # A 3 kW hourly average is 3 kWh, not the sum of the two kW values.
        self.assertEqual(F.average_w(periods, NOW + timedelta(minutes=15), NOW + timedelta(minutes=30)), 2000)

    def test_zero_is_a_forecast_not_missing(self):
        periods = F.parse_state(sensor([record(NOW, 0)]), NOW)
        self.assertEqual(F.average_w(periods, NOW, NOW + timedelta(minutes=15)), 0)

    def test_missing_intervals_are_not_zero(self):
        periods = F.parse_state(sensor([record(NOW, 2)]), NOW)
        self.assertIsNone(F.average_w(periods, NOW, NOW + timedelta(hours=1)))
        self.assertIsNone(F.average_w(periods, NOW - timedelta(minutes=15), NOW))

    def test_offset_and_dst_are_compared_in_utc(self):
        records = [{"period_start": "2026-10-25T02:00:00+02:00", "pv_estimate": 2},
                   {"period_start": "2026-10-25T02:00:00+01:00", "pv_estimate": 4}]
        now = datetime(2026, 10, 25, tzinfo=timezone.utc)
        state = sensor(records)
        state["last_updated"] = now.isoformat()
        periods = F.parse_state(state, now)
        self.assertEqual(len(periods), 2)
        self.assertEqual((periods[1][0] - periods[0][0]).total_seconds(), 3600)

    def test_hourly_attribute_is_supported_without_double_counting(self):
        s = sensor([], detailedHourly=[record(NOW, 3)])
        periods = F.parse_state(s, NOW)
        self.assertEqual(F.average_w(periods, NOW, NOW + timedelta(hours=1)), 3000)
        s["attributes"]["detailedForecast"] = [record(NOW, 2), record(NOW + timedelta(minutes=30), 4)]
        self.assertEqual(len(F.parse_state(s, NOW)), 2)

    def test_stale_unknown_and_unavailable_sensors(self):
        s = sensor([record(NOW, 2)])
        s["last_updated"] = (NOW - timedelta(hours=37)).isoformat()
        self.assertEqual(F.parse_state(s, NOW), [])
        for state in ("unknown", "unavailable"):
            s = sensor([record(NOW, 2)])
            s["state"] = state
            self.assertEqual(F.parse_state(s, NOW), [])

    def test_invalid_values_and_naive_timestamps_are_ignored(self):
        records = [record(NOW, v) for v in (None, -1, float("nan"), float("inf"), True)]
        records += [{"period_start": "2026-11-10T12:00:00", "pv_estimate": 2}, {}, None]
        self.assertEqual(F.parse_state(sensor(records), NOW), [])

    def test_conflicting_or_overlapping_rows_are_rejected(self):
        for records in ([record(NOW, 2), record(NOW, 4)],
                        [record(NOW, 2), record(NOW + timedelta(minutes=15), 4)]):
            self.assertEqual(F.parse_state(sensor(records), NOW), [])

    def test_disabled_source_never_reads_ha(self):
        self.settings.clear()
        with patch.object(F, "_read_state", side_effect=AssertionError("No HA reads")):
            self.assertIsNone(F.power_at(NOW))
            self.assertIsNone(F.power_at(NOW.replace(tzinfo=None)))

    def test_fetches_are_cached_and_changed_settings_invalidate_cache(self):
        s = sensor([record(NOW, 2)])
        s["last_updated"] = datetime.now(timezone.utc).isoformat()
        with patch.object(F, "_read_state", return_value=s) as read:
            self.assertEqual(F.power_at(NOW), 2000)
            self.assertEqual(F.power_at(NOW + timedelta(minutes=15)), 2000)
            self.assertEqual(read.call_count, 1)
            self.settings["solar_forecast_entities"] = ["sensor.solcast_tomorrow"]
            F.power_at(NOW)
            self.assertEqual(read.call_count, 2)

    def test_request_failure_does_not_reuse_expired_forecasts(self):
        s = sensor([record(NOW, 2)])
        s["last_updated"] = datetime.now(timezone.utc).isoformat()
        with patch.object(F, "_read_state", return_value=s):
            self.assertEqual(F.power_at(NOW), 2000)
        F._CACHE["until"] = 0
        with patch.object(F, "_read_state", side_effect=TimeoutError):
            self.assertIsNone(F.power_at(NOW))
            self.assertEqual(F.snapshot()["state"], "unavailable")

    def test_conflicting_selected_sensors_are_not_summed(self):
        self.settings["solar_forecast_entities"].append("sensor.solcast_rooftop")
        a, b = sensor([record(NOW, 2)]), sensor([record(NOW, 1)])
        for s in (a, b):
            s["last_updated"] = datetime.now(timezone.utc).isoformat()
        with patch.object(F, "_read_state", side_effect=[a, b]):
            self.assertIsNone(F.power_at(NOW))
            self.assertEqual(F.snapshot()["state"], "conflict")

    def test_duplicate_selected_data_are_counted_once(self):
        self.settings["solar_forecast_entities"].append("sensor.solcast_copy")
        s = sensor([record(NOW, 2)])
        s["last_updated"] = datetime.now(timezone.utc).isoformat()
        with patch.object(F, "_read_state", return_value=s):
            self.assertEqual(F.power_at(NOW), 2000)

    def test_selection_is_validated(self):
        for source, entities in [("unknown", []), ("solcast_ha", []), ("solcast_ha", "sensor.x"),
                                 ("solcast_ha", ["sensor.x/../../config"]), ("solcast_ha", ["switch.x"]),
                                 ("solcast_ha", ["sensor.x"] * 8)]:
            with self.assertRaises(ValueError):
                F.validate(source, entities)
        self.assertEqual(F.validate("solcast_ha", ["sensor.x", "sensor.x"]), ["sensor.x"])

    def test_weather_preserves_zero_and_clear_sky_fallback(self):
        import weather
        profile = {(NOW.month, NOW.hour): 4000}
        with patch.object(F, "power_at", return_value=0):
            self.assertEqual(weather.get_smart_solar_w(50, NOW, profile), 0)
            self.assertEqual(weather.get_smart_solar_w(0, NOW, profile, use_external=False), 4000)
        with patch.object(F, "power_at", return_value=None):
            self.assertEqual(weather.get_smart_solar_w(0, NOW, profile), 4000)


if __name__ == "__main__":
    unittest.main()
