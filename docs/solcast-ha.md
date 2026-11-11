# Solcast through Home Assistant

Solcast is an optional forecast input. EnergyWizard reads the existing Home
Assistant integration rather than implementing another Solcast client. It does
not store a Solcast API key, call the Solcast API, trigger forecast updates or
change the integration's API quota. The internal forecast remains the default.

## Setup

1. Configure your rooftops, capacity, orientation and tilt in your Solcast account.
2. Install [Solcast PV Solar Forecast](https://github.com/BJReplay/ha-solcast-solar#installation)
   through HACS and add it under Home Assistant **Settings → Devices & services**.
   Enter the Solcast API key there.
3. Enable detailed forecast attributes in the integration options. The aggregate
   daily sensors must expose `detailedForecast` or `detailedHourly`.
4. In EnergyWizard's **Solar** page, choose **Solcast via Home Assistant**. Select
   the aggregate daily sensors for today, tomorrow and subsequent days, then save.
   Do not combine aggregate sensors with individual rooftop sensors. Sensors can
   have custom entity IDs; no house-specific IDs are built into the adapter.

The in-app setup instructions, validation messages and source status are
translatable through the existing Swedish/English/Czech catalog system. Swedish
is the source language; the English and Czech catalogs contain the same new keys.

## Data and fallback

The adapter reads `pv_estimate` and timezone-aware `period_start`. The documented
aggregate `detailedForecast` attribute contains average **kW per 30-minute period**;
`detailedHourly` contains average kW per hour. The daily sensor's state in kWh is
never treated as instantaneous power. Native slots are mapped onto quarter-hour
planning slots. Hourly displays and day totals use time-weighted hourly averages.

Only the aggregate attributes are used. Per-rooftop attributes are ignored;
conflicting selected intervals invalidate the external source instead of adding
them together. Identical duplicate intervals are counted once.

Unavailable/unknown sensors, updates older than 36 hours, malformed values,
timezone-free timestamps and gaps do not become zero production. EnergyWizard
uses its existing learned/weather estimate for uncovered periods. Explicit zero
forecast values are valid. HA reads are cached for five minutes per process;
failed refreshes do not keep an expired cached forecast alive.

The selected forecast feeds current/next production estimates, the battery plan,
timeline, plan clock, daily forecast and mobile price chart. Existing planning
preferences and calibration still apply. The clear-sky reference used for sunny
weather classification stays internal and is not replaced with a cloudy forecast.
Measured PV sensors and export-control drivers are unaffected.

The adapter does not alter weather coordinates or the existing internal model.
Its fallback therefore retains the limitations of the current installation's
internal forecast. Data availability is not a guarantee of forecast accuracy.

## Validation

Focused tests cover unit conversion, zero versus missing data, time-weighted
averages, DST offsets, malformed/stale inputs, interval conflicts, cached reads,
failed refreshes, selection validation and the internal-model fallback. Run:

```sh
PYTHONPATH=smartbox python -m unittest discover -s tests -p test_ha_solar_forecast.py
```

The upstream PostgreSQL/application suite and hardware behavior require the
complete project environment. No write actions are added by this adapter.
