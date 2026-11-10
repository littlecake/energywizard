# Australian dollars and dynamic Home Assistant prices

In the web dashboard, open **Settings → Electricity prices and fees**, select **Australia**, and save. The preset uses **AUD (A$)**, 10% GST, and zero additional buying/selling fees. Enter your own fees from your tariff; values are in AUD per kWh. Selecting a currency does not convert prices or historical amounts between currencies.

The price timezone defaults to `Australia/Sydney`. Change it to your location, for example `Australia/Brisbane`, `Australia/Adelaide`, `Australia/Perth`, or `Australia/Darwin`. This setting controls price-day boundaries, price timestamp parsing, and the electricity tariff's local hours. It does not migrate all device schedules or change the timezone of other dashboard/history queries, which still use their existing timezone handling.

Select a Home Assistant price sensor under **Price source**, such as Amber's **General Forecast** sensor. Swedish `elprisetjustnu.se` prices are never fetched for an Australian installation. Monetary labels in the web and mobile apps use the selected currency.

## GST and units

Amber's Home Assistant prices are already expressed in dollars per kWh and include GST. Keep **The sensor price already includes VAT/GST** enabled for that feed. The GST preset is used by the existing cost formulas; it is not added again to an inclusive buying price. Selling-price tax treatment and extra fees remain configurable. Verify these settings against your tariff.

The importer also accepts cents per kWh and dollars per MWh using the sensor's unit metadata. Prices remain in the configured currency; no foreign exchange conversion takes place. Existing database/JSON field names such as `sek_per_kwh` and `saved_kr` are retained for compatibility.

## Forecast refreshes and the current price

**Published prices** offers three choices:

- **Automatic**: Amber sensors with a `forecasts` attribute refresh every five minutes. Other recognized feeds keep published prices fixed.
- **Final once published**: insert each published slot once, suitable for fixed day-ahead feeds.
- **Refresh current and future prices**: opt any supported HA price feed into five-minute refreshes.

Refreshes run from the engine's normal price-check cycle. After a restart, the engine probes the selected HA feed once even if prices are already stored. Dynamic sources import all available upcoming slots, including tomorrow before the Swedish 13:30 publication check. Failed refreshes retain stored prices and retry on the next engine cycle.

Completed intervals remain unchanged. The current interval and future forecasts may be updated until their end timestamps pass. Updates are atomic within a database transaction. The importer also canonicalizes Amber's `:00:01` inclusive starts to their five-/thirty-minute boundaries, replacing active old keys so that a one-second hole or overlapping old forecast does not remain.

The forecast sensor's state is **not** used as the actual current price. When the selected Amber entity ends in `_forecast`, EnergyWizard tries the corresponding `_price` entity. For a renamed sensor, set **Current price sensor** explicitly. The current-price sensor must provide `start_time` and `end_time` attributes covering the current time; stale or unavailable readings leave the latest forecast in use. Completed history cannot be reconstructed from actual readings that were unavailable while a slot was current.

Five-minute prices are averaged by interval duration into the planner's fifteen-minute slots. Australian daylight-saving days therefore contain 92 or 100 quarters rather than an assumed 96. Missing profile coverage is filled in memory for planning; it is not written as actual historical prices.

## Environment configuration

The same settings can be supplied through environment variables visible to the engine and the apps. Existing web-saved price settings take precedence over these defaults.

```dotenv
PRICE_COUNTRY=AU
PRICE_CURRENCY=AUD
PRICE_TIMEZONE=Australia/Sydney
PRICE_SOURCE=ha_nordpool
NORDPOOL_HA_ENTITY=sensor.amber_general_forecast
PRICE_INCLUDES_VAT=true
PRICE_FINAL=auto
# Set this if the current-price entity has a custom name:
# PRICE_CURRENT_ENTITY=sensor.amber_general_price
```

If using Docker Compose, add these variables to the appropriate services' `environment` configuration; putting a new variable in `.env` alone does not automatically inject it into containers. Home Assistant add-on users can use the dashboard settings instead.
